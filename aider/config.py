class Config:
    args = None

    @classmethod
    def initialize(cls, parsed_args):
        cls.args = parsed_args
