from .cli import main, config_parser


if __name__ == "__main__":
    args = config_parser.parse_args()
    main(args)
