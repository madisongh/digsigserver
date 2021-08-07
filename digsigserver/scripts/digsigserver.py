import argparse
import os
import sys
from digsigserver.server import app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--address', help='address to host on', default='0.0.0.0')
    parser.add_argument('-p', '--port', help='port to host on', type=int, default=9999)
    parser.add_argument('-d', '--debug', help='enable debug logging', action='store_true')
    args = parser.parse_args()
    if not os.getenv('DIGSIGSERVER_KEYFILE_URI'):
        raise RuntimeError('Environment variable DIGSIGSERVER_KEYFILE_URI not set')
    app.run(host=args.address, port=args.port, debug=args.debug)


if __name__ == '__main__':
    # noinspection PyBroadException
    try:
        main()
        sys.exit(0)
    except SystemExit:
        pass
    except Exception:
        import traceback

        traceback.print_exc(5)
        sys.exit(1)
