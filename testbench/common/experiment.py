class ExperimentAbortedException(Exception):

    def __init__(self) -> None:
        super().__init__("Experiment was Aborted")


class ExperimentFailedException(Exception):

    def __init__(self, reason: str) -> None:
        super().__init__(f"Experiment has Failed: {reason}")


class ExperimentAlreadyRunningException(Exception):

    def __init__(self) -> None:
        super().__init__("Experiment is already Running")
