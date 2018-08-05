#!/usr/bin/python3

import argparse
import database
import database_proto
import datetime
import default_nemesis_proto
import nemesis_pb2
import os
import queue
import signal
import sys
import threading
import time
import zmq

NEMESIS_DATA_PATH = os.getenv('NEMESIS_DATA')

def get_priority(user_id):
    role_dict = {
        'pj' : 100,
        'superadmin' : 75,
        'admin' : 50,
        'user' : 25,
        'ban' : 0
    }

    role = database.session.query(database.User).filter(database.User.id == user_id).first().role
    return role_dict[role]

def get_task(task_id):
    task_db = database.session.query(database.Task).filter(database.Task.id == task_id)
    result = default_nemesis_proto.default_Task()

    with open(os.path.join(NEMESIS_DATA_PATH, 'tasks', str(task_id), 'src', 'checker'), 'rb') as checker_source:
        result.checker = checker_source.read()

    with open(os.path.join(NEMESIS_DATA_PATH, 'tasks', str(task_id), 'src', 'solution'), 'rb') as solution_source:
        result.solution = solution_source.read()

    groups = {}

    for test in database.session.query(database.Test).filter(database.Test.task_id == task_id):
        tt = default_nemesis_proto.default_Task_Group_Test()
        tt.id = test.test_id
        tt.time_limit = test.time_limit
        tt.memory_limit = test.memory_limit
        with open(os.path.join(NEMESIS_DATA_PATH, 'tasks', str(task_id), 'tests', str(test.group_id), 'in', str(test.test_id)), 'rb') as input_file:
            tt.input = input_file.read()
        if test.group_id in groups:
            groups[test.group_id].append(tt)
        else:
            groups[test.group_id] = [tt]

    for w in groups:
        grp = default_nemesis_proto.default_Task_Group()
        grp.id = w
        grp.number_of_tests = len(groups[w])
        for test in groups[w]:
            grp.tests.extend([test])
        result.groups.extend([grp])

    result.number_of_groups = len(groups)

    return result

def get_proto(inst):
    if inst.custom_id != None:
        result = default_nemesis_proto.default_CustomInvocation()
        result.id = inst.custom_id
        CI_DB = database.session.query(database.Custom_Invocation).filter(database.Custom_Invocation.id == result.id).first()
        CI_DB.state = 'running'
        database.session.commit()
        result.user_id =  CI_DB.user_id
        result.lang = database_proto.rev_parse_lang(CI_DB.lang)
        with open(os.path.join(NEMESIS_DATA_PATH, 'customs', str(result.id), 'src'), 'rb') as source:
            result.source = source.read()
        with open(os.path.join(NEMESIS_DATA_PATH, 'customs', str(result.id), 'in'), 'rb') as input_file:
            result.test.id = 1
            result.test.time_limit = 5000 # 5s
            result.test.memory_limit = 65536 # 64 MB
            result.test.output = b''
            result.test.input = input_file.read()
        job = default_nemesis_proto.default_Job()
        job.custom = True
        job.custom_job.CopyFrom(result)
        return job
    if inst.submit_id != None:
        result = default_nemesis_proto.default_Submit()
        result.id = inst.submit_id
        NS = database.session.query(database.Submit).filter(database.Submit.id == result.id).first()
        NS.state = 'running'
        database.session.commit()

        result.task.CopyFrom(get_task(NS.task_id))
        result.user_id = NS.user_id
        result.lang = database_proto.rev_parse_lang(NS.lang)
        result.subsection_id = NS.subsection_id
        result.rejudge = inst.rejudge

        with open(os.path.join(NEMESIS_DATA_PATH, 'submits', str(result.id), 'src'), 'rb') as source:
            result.code = source.read()

        job = default_nemesis_proto.default_Job()
        job.custom = False
        job.submit.CopyFrom(result)
        return job
    print('get_proto(): ERROR job without type')


class Instance():

    def __init__(self, submit_id = None, custom_id = None, priority = 0, rejudge = False):
        self.submit_id = submit_id
        self.custom_id = custom_id
        self.priority = priority
        self.rejudge = rejudge

    def __repr__(self):
        return '<submit_id=%s, custom_id=%s, priority=%s>' % (self.id, self.submit_id, self.custom_id, self.priority)

    def __lt__(self, other):
        if self.priority != other.priority:
            return self.priority > other.priority
        if self.submit_id is not None and other.submit_id is not None:
            return self.submit_id < other.submit_id
        if self.submit_id is not None:
            return True
        return False

def isEq(instance, job):
    if job.custom == True:
        return job.custom_status.id == instance.custom_id
    else:
        return job.status.id == instance.submit_id

def create_custom(proto):
    CI = database.Custom_Invocation(user_id = proto.user_id, state = 'waiting', lang = database_proto.parse_lang(proto.lang), date = datetime.datetime.now(), time_usage = -1, memory_usage = -1)
    database.session.add(CI)
    database.session.commit()
    if not os.path.exists(os.path.join(NEMESIS_DATA_PATH, 'customs', str(CI.id))):
        os.makedirs(os.path.join(NEMESIS_DATA_PATH, 'customs', str(CI.id)))
    with open(os.path.join(NEMESIS_DATA_PATH, 'customs', str(CI.id), 'src'), 'wb') as source:
        source.write(proto.source)
    with open(os.path.join(NEMESIS_DATA_PATH, 'customs', str(CI.id), 'in'), 'wb') as input_file:
        input_file.write(proto.test.input)
    inst = Instance(custom_id = CI.id, priority = get_priority(proto.user_id), rejudge = False)
    return inst

def create_submit(proto):
    rejudge = False

    CD = database.session.query(database.Submit).filter(database.Submit.id == proto.id).first()
    if CD:
        rejudge = True

    if rejudge:
        CD.state = 'waiting'
        CD.points = 0
        CD.compiled = False
        CD.acm = False
    else:
        LS = database.Submit(user_id = proto.user_id, task_id = proto.task_id, state = 'waiting', lang = database_proto.parse_lang(proto.lang), date = datetime.datetime.now(), points = 0, compiled = False, acm = False, subsection_id = proto.subsection_id)
        database.session.add(LS)
    database.session.commit()

    if not rejudge:
        if not os.path.exists(os.path.join(NEMESIS_DATA_PATH, 'submits', str(LS.id))):
            os.makedirs(os.path.join(NEMESIS_DATA_PATH, 'submits', str(LS.id)))
        with open(os.path.join(NEMESIS_DATA_PATH, 'submits', str(LS.id), 'src'), 'wb') as source:
            source.write(proto.code)
        inst = Instance(submit_id = LS.id, priority = get_priority(proto.user_id), rejudge = False)
    else:
        inst = Instance(submit_id = CD.id, priority = get_priority(proto.user_id), rejudge = True)
    return inst

class Worker():

    def __init__(self, worker_id, host, addr, port, heartbeat = None, instance = None):
        self.worker_id = worker_id
        self.host = host
        self.port = port
        self.heartbeat = heartbeat
        self.instance = instance
        self.addr = addr

    def __repr__(self):
        return "<id=%s, host='%s', addr=%s, port=%s, heartbeat='%s', instance='%s'>" % (self.worker_id, self.host, self.addr, self.port, self.heartbeat, self.instance)


mutex = threading.Lock()
workers = {}
Jobs = queue.PriorityQueue()
Rated = queue.Queue()

def heartbeats(addr, port):
    while True:
        try:
            context = zmq.Context()
            socket = context.socket(zmq.PULL)
            socket.bind("tcp://%s:%s" % (addr, port))

            while True:
                msg = socket.recv()
                data = nemesis_pb2.Heartbeat()

                try:
                    data.ParseFromString(msg)

                    if data.IsInitialized() == False:
                        continue

                    mutex.acquire()
                    if data.id in workers:
                        if time.time() - workers[data.id].heartbeat > 10.0:
                            print('heartbeats(): worker {} now working'.format(data.id))
                        workers[data.id].heartbeat = time.time()
                    else:
                        workers[data.id] = Worker(worker_id = data.id, host = data.name, addr = data.addr, port = data.port, heartbeat = time.time())
                        print('heartbeats(): create worker {}'.format(workers[data.id]))
                    mutex.release()
                except:
                    print('heartbeats(): data is corrupted')
        except Exception as e:
            print(e, file=sys.stderr)
            continue

def fix_workers():
    while True:
        try:
            while True:
                time.sleep(5)
                mutex.acquire()
                for worker in workers:
                    if time.time() - workers[worker].heartbeat >= 10 and workers[worker].instance != None:
                        print('fix_workers(): {} is corrupted'.format(worker))
                        Jobs.put(workers[worker].instance)
                        workers[worker].instance = None
                mutex.release()
        except Exception as e:
            print(e, file=sys.stderr)
            continue

def run(data, addr, port, worker_id):
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://%s:%s" % (addr, port))

    print('run(): send ({},{}) to {}:{}'.format(data.submit.id, data.custom_job.id, addr, port))

    socket.send(data.SerializeToString())
    msg = socket.recv()
    socket.close()
    result = nemesis_pb2.JobReturn()
    try:
        result.ParseFromString(msg)
        if result.IsInitialized() == False:
            Jobs.put(workers[worker_id].instance)
            workers[worker_id].instance = None
            return
        Rated.put(result)
        print('run(): get result for ({},{})'.format(result.status.id, result.custom_status.id))
        mutex.acquire()
        workers[worker_id].instance = None
        print('run(): {} is free'.format(worker_id))
        mutex.release()
        return
    except Exception as e:
        print('run(): data is corrupted')
        print(e, file=sys.stderr)
    mutex.release()


def server(addr, port):
    while True:
        try:
            context = zmq.Context()
            socket = context.socket(zmq.PULL)
            socket.bind("tcp://%s:%s" % (addr, port))
            while True:
                msg = socket.recv()
                job = nemesis_pb2.LogicJob()
                try:
                    job.ParseFromString(msg)
                except:
                    print('server(): data is corrupted')
                    continue
                if job.IsInitialized() == False:
                    print('server(): job isn\'t initialized')
                    continue

                if job.custom == True:
                    inst = create_custom(job.custom_job)
                    Jobs.put(inst)
                else:
                    inst = create_submit(job.submit)
                    Jobs.put(inst)
        except Exception as e:
            print(e, file=sys.stderr)
            continue;

def compute_jobs():
    while True:
        try:
            while True:
                if Jobs.empty():
                    time.sleep(5)
                    continue

                search_free_worker = True
                while search_free_worker:
                    mutex.acquire()
                    for w in workers:
                        if workers[w].instance == None and time.time() - workers[w].heartbeat <= 5.0:
                            print('compute_jobs(): start job in {}'.format(w))
                            search_free_worker = False
                            workers[w].instance = Jobs.get()
                            proto = get_proto(workers[w].instance)
                            t = threading.Thread(target = run, args = (proto, workers[w].addr, workers[w].port, w))
                            t.daemon = True
                            t.start()
                            break
                    mutex.release()

                    if search_free_worker:
                        print('compute_jobs(): waiting for free worker')
                        time.sleep(1)
        except Exception as e:
            print(e, file=sys.stderr)
            continue

def compute_rated():
    while True:
        try:
            while True:
                if Rated.empty():
                    time.sleep(1)
                    continue

                submition = Rated.get()

                if submition.custom == True:
                    CI_DB = database.session.query(database.Custom_Invocation).filter(database.Custom_Invocation.id == submition.custom_status.id).first()
                    CI_DB.time_usage = submition.custom_status.time
                    CI_DB.memory_usage = submition.custom_status.memory
                    CI_DB.state = database_proto.parse_status_code(submition.custom_status.status, False, True, submition.custom_status.compiled, submition.system_error)
                    with open(os.path.join(NEMESIS_DATA_PATH, 'customs', str(CI_DB.id), 'compile_log'), 'wb') as compile_log:
                        compile_log.write(bytes(submition.custom_status.compile_log.encode('utf-8')))
                    with open(os.path.join(NEMESIS_DATA_PATH, 'customs', str(CI_DB.id), 'output'), 'wb') as output:
                        output.write(submition.custom_status.out)
                else:
                    NS_DB = database.session.query(database.Submit).filter(database.Submit.id == submition.status.id).first()
                    NS_DB.points = submition.status.points
                    NS_DB.compiled = submition.status.compiled
                    NS_DB.acm = submition.status.acm
                    NS_DB.state = database_proto.parse_status_code(submition.status.status, submition.status.acm, False, submition.status.compiled, submition.system_error)
                    with open(os.path.join(NEMESIS_DATA_PATH, 'submits', str(NS_DB.id), 'compile_log'), 'wb') as compile_log:
                        compile_log.write(bytes(submition.status.compile_log.encode('utf-8')))

                    if submition.status.rejudge:
                        tests = database.session.query(database.Test_submit).filter(database.Test_submit.submit_id == submition.status.id).all()
                        for test in tests:
                            database.session.delete(test)
                            database.session.commit()

                    for grp in submition.status.groups:
                        for tt in grp.tests:
                            test = database.Test_submit(submit_id = submition.status.id, group_id = grp.id, test_id = tt.id, time_usage = tt.time, memory_usage = tt.memory, status = database_proto.parse_status_code(tt.status, tt.verdict, False, submition.status.compiled, submition.system_error))
                            database.session.add(test)
                            database.session.commit()

                database.session.commit()
        except Exception as e:
            print(e, file=sys.stderr)
            continue

def handler_force_lock_thread():
    mutex.acquire()

def handler(signum, frame):
    print('logic.py: shutting down ({})'.format(signum))

    thread_lock = threading.Thread(target = handler_force_lock_thread)
    thread_lock.daemon = True
    thread_lock.start()

    time.sleep(120)

    for inst in database.session.query(database.Custom_Invocation).filter(database.Custom_Invocation.state == 'running').all():
        inst.state = 'waiting'
    database.session.commit()

    for inst in database.session.query(database.Submit).filter(database.Submit.state == 'running').all():
        inst.state = 'waiting'
    database.session.commit()

    sys.exit(1)


def main_local():
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
    parser = argparse.ArgumentParser(description='Nemesis Logic')
    parser.add_argument('--addr', dest='addr', default='*', type=str, help='address')
    parser.add_argument('--port', dest='port', default=5555, type=int, help='port')
    parser.add_argument('--name', dest='name', default='LOGIC_LOCALHOST', type=str, help='logic name')
    parser.add_argument('--heartbeat_port', dest='heartbeat_port', default=5550, type=int, help='heartbeat port')

    args = parser.parse_args()

    database.init_db()

    thread_server = threading.Thread(target = server, args=(args.addr, args.port))
    thread_compute_jobs = threading.Thread(target = compute_jobs)
    thread_compute_rated = threading.Thread(target = compute_rated)
    thread_heartbeat = threading.Thread(target = heartbeats, args = (args.addr, args.heartbeat_port))
    thread_fix_workers = threading.Thread(target = fix_workers)

    thread_server.daemon = True
    thread_compute_jobs.daemon = True
    thread_compute_rated.daemon = True
    thread_heartbeat.daemon = True
    thread_fix_workers.daemon = True

    for inst in database.session.query(database.Custom_Invocation).filter(database.Custom_Invocation.state == 'waiting').all():
        Jobs.put(Instance(submit_id = None, custom_id = inst.id, priority = 5))

    for inst in database.session.query(database.Submit).filter(database.Submit.state == 'waiting').all():
        Jobs.put(Instance(submit_id = inst.id, custom_id = None, priority = 10))

    thread_server.start()
    thread_compute_jobs.start()
    thread_compute_rated.start()
    thread_heartbeat.start()
    thread_fix_workers.start()

    while True:
        time.sleep(10)
        for w in workers:
            if time.time() - workers[w].heartbeat > 5.0:
                print('main(): {} not responding'.format(w))
            elif workers[w].instance == None:
                print('main(): {} is free'.format(w))
            else:
                print('main(): {} is busy'.format(w))


def main():
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
    
    addr = os.getenv("LOGIC_ADDR")
    port = os.getenv("LOGIC_PORT")
    name = os.getenv("LOGIC_NAME")
    heartbeat_port = os.getenv("LOGIC_HEARTBEAT_PORT")

    database.init_db()

    thread_server = threading.Thread(target = server, args=(addr, int(port)))
    thread_compute_jobs = threading.Thread(target = compute_jobs)
    thread_compute_rated = threading.Thread(target = compute_rated)
    thread_heartbeat = threading.Thread(target = heartbeats, args = (addr, int(heartbeat_port)))
    thread_fix_workers = threading.Thread(target = fix_workers)

    thread_server.daemon = True
    thread_compute_jobs.daemon = True
    thread_compute_rated.daemon = True
    thread_heartbeat.daemon = True
    thread_fix_workers.daemon = True

    for inst in database.session.query(database.Custom_Invocation).filter(database.Custom_Invocation.state == 'waiting').all():
        Jobs.put(Instance(submit_id = None, custom_id = inst.id, priority = 5))

    for inst in database.session.query(database.Submit).filter(database.Submit.state == 'waiting').all():
        Jobs.put(Instance(submit_id = inst.id, custom_id = None, priority = 10))

    thread_server.start()
    thread_compute_jobs.start()
    thread_compute_rated.start()
    thread_heartbeat.start()
    thread_fix_workers.start()

    while True:
        time.sleep(10)
        for w in workers:
            if time.time() - workers[w].heartbeat > 5.0:
                print('main(): {} not responding'.format(w))
            elif workers[w].instance == None:
                print('main(): {} is free'.format(w))
            else:
                print('main(): {} is busy'.format(w))



if __name__ == '__main__':
    main()
