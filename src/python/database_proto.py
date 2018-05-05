import database
import nemesis_pb2

def parse_status_code(code, acm, isCustom, compiled, system_error):
    result = 'SYS'

    if system_error:
        return 'SYS'

    if compiled == False:
        result = 'CE'
    elif code == nemesis_pb2.OK and acm == True:
        result = 'AC'
    elif code == nemesis_pb2.OK and isCustom == True:
        result = 'OK'
    elif code == nemesis_pb2.OK and isCustom == False:
        result = 'WA'
    elif code == nemesis_pb2.TLE:
        result = 'TLE'
    elif code == nemesis_pb2.MLE:
        result = 'MLE'
    elif code == nemesis_pb2.ILL:
        result = 'ILL'
    elif code == nemesis_pb2.SEG:
        result = 'SEG'
    elif code == nemesis_pb2.FPE:
        result = 'FPE'
    elif code == nemesis_pb2.RE:
        result = 'RE'
    elif code == nemesis_pb2.OE:
        result = 'OE'
    elif code == nemesis_pb2.SYS:
        result = 'SYS'
    elif code == nemesis_pb2.FSZ:
        result = 'FSZ'
    else:
        result = 'SYS'

    return result

def parse_lang(lang):
    result = 'UNKNOW'

    if lang == nemesis_pb2.CC:
        result = 'CC'
    elif lang == nemesis_pb2.CXX:
        result = 'CXX'
    elif lang == nemesis_pb2.RAM:
        result = 'RAM'

    return result

def rev_parse_lang(lang):
    result = 'UNKNOW'

    if lang == 'CC':
        result = nemesis_pb2.CC
    elif lang == 'CXX':
        result = nemesis_pb2.CXX
    elif lang == 'RAM':
        result = nemesis_pb2.RAM

    return result

def create_submit_from_status(proto, insert_date):
    result = database.Submit(user_id = proto.user_id, task_id = proto.task_id, state = parse_status_code(proto.status, proto.acm, False), lang = parse_lang(proto.lang), date = insert_date, points = proto.points, compiled = proto.compiled, acm = proto.acm, subsection_id = proto.subsection_id)
    return result

def create_custom_invocation_from_status(proto, insert_date):
    result = database.Custom_Invocation(user_id = proto.user_id, state = parse_status_code(proto.status, False, True), lang = parse_lang(proto.lang), date = insert_date, time_usage = proto.time, memory_usage = proto.memeory)
    return result

def create_tests_from_status(proto):
    tests = []

    group_id = 0
    for group in proto.groups:
        group_id += 1
        test_id = 0
        for test in group.tests:
            test_id += 1
            Test = database.Test(submit_id = proto.id, group_id = group_id, test_id = test_id, time_usage = test.time, memory_usage = test.memory, status = parse_status_code(test.status, test.verdict, False))
            tests.append(Test)

    return tests
