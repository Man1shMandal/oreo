import sys

if sys.argv[1:2] == ["web"]:
    from .web import main
    main(sys.argv[2:])
else:
    from .cli import main
    main()
