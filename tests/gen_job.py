import argparse
import default_nemesis_proto
import nemesis_pb2
import os


def main():
    parser = argparse.ArgumentParser(description="Generate Nemesis protobuf")
    parser.add_argument("--out", dest="out", help="output")
    parser.add_argument("--lang", dest="lang", default=None, help="submit language")
    parser.add_argument("--source", dest="source", default=None, help="source file")
    parser.add_argument("--user_id", dest="user_id", type=int, default=1, help="user id")
    parser.add_argument("--task_id", dest="task_id", type=int, default=1, help="task id")

    args = parser.parse_args()

    lang_dict = {
        "CC": nemesis_pb2.CC,
        "CXX": nemesis_pb2.CXX,
        "RAM": nemesis_pb2.RAM
    }

    job = nemesis_pb2.LogicJob()
    job.custom = False
    job.custom_job.id = 0
    job.custom_job.user_id = 0
    job.custom_job.lang = nemesis_pb2.CXX
    job.custom_job.test.id = 0
    job.custom_job.test.time_limit = -1
    job.custom_job.test.memory_limit = -1
    job.custom_job.test.input = b''
    job.custom_job.test.output = b''
    job.custom_job.source = b''
    job.submit.id = 0
    job.submit.user_id = args.user_id
    job.submit.task_id = args.task_id
    job.submit.lang = nemesis_pb2.CXX
    job.submit.subsection_id = 1
    job.submit.code = open(args.source, 'rb').read()

    open(args.out, 'wb').write(job.SerializeToString())
    #print(job)

if __name__ == "__main__":
    main()
