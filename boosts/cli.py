"""命令行入口：跑活动加成时段样例。"""

import argparse

from .core import Boosts


def build_parser():
    parser = argparse.ArgumentParser(prog="boost-window", description="活动加成时段")
    parser.add_argument("--sample", default="boundary", help="boundary / priority / dup / scan")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.sample == "boundary":
        book = Boosts()
        book.add("a1", 1000, 2000, "xp", 1.5)
        print("count=%d" % len(book.active_at(2000)))
    elif args.sample == "priority":
        book = Boosts()
        book.add("a1", 0, 100, "xp", 1.5, priority=1)
        book.add("a2", 0, 100, "xp", 2.0, priority=5)
        active = book.active_at(50)
        print("rate=%.1f" % active[0][1])
    elif args.sample == "dup":
        book = Boosts()
        book.add("a1", 0, 100, "xp", 1.5)
        second = book.add("a1", 0, 100, "xp", 9.0)
        active = book.active_at(50)
        print("second=%s rate=%.1f" % (str(second).lower(), active[0][1]))
    elif args.sample == "scan":
        book = Boosts()
        for index in range(3000):
            book.add("a-%d" % index, 0, 1000000, "kind-%d" % index, 1.0)
        for _ in range(3000):
            book.active_at(0)
        print("scanned=%d" % book.scanned_count())
    else:
        raise SystemExit("需要 --sample boundary|priority|dup|scan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
