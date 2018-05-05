import argparse
import nemesis_pb2
import zmq

def run(data, addr, port):
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)

    socket.connect("tcp://%s:%s" % (addr, port))

    print("Send data")
    socket.send(data)
    socket.close()


def main():
    parser = argparse.ArgumentParser(description="Nemesis client")
    parser.add_argument('--submit', dest="submit", required=True, help="data file")
    parser.add_argument('--addr', dest="addr", type=str, default="localhost", help="address")
    parser.add_argument('--port', dest="port", type=str, default="5556", help="port")

    args = parser.parse_args()

    data = nemesis_pb2.LogicJob()

    with open(args.submit, 'rb') as data_file:
        data.ParseFromString(data_file.read())

    run(data.SerializeToString(), args.addr, args.port)


if __name__ == "__main__":
    main()
