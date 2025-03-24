from dataclasses import dataclass


submission_status_to_str = {
    0: "closed",
    1: "open",
    2: "lcc_only"
}


@dataclass
class Format:
    """
    type: object
    properties:
      id:
        type: int
        description: The ID of the format.
      name:
        type: string
        description: The name of the format.
      hidden:
        type: boolean
        description: Whether maps with this format should be hidden.
      run_submission_status:
        type: int
        description: Whether submissions are open, closed, ...
        enum: ["open", "closed", "lcc_only"]
      map_submission_status:
        type: int
        description: Whether map submissions are open, closed, ...
        enum: ["open", "closed"]
    """

    id: int
    name: str
    map_submission_wh: str | None
    run_submission_wh: str | None
    hidden: bool
    run_submission_status: int
    map_submission_status: int
    emoji: str | None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "hidden": self.hidden,
            "run_submission_status": submission_status_to_str.get(self.run_submission_status, "closed"),
            "map_submission_status": submission_status_to_str.get(self.map_submission_status, "closed"),
        }
