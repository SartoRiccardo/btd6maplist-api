from dataclasses import dataclass
import src.utils.formats.formatinfo


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
      proposed_difficulties:
        type: array
        description: |
          What difficulties can be proposed by the map submitters. If it's null,
          it's something dynamic that you have to fetch on the fly (e.g. retro maps
          for the Nostalgia Pack).
        items:
          type: string
        nullable: true
    ---
    FullFormat:
      allOf:
      - $ref: "#/components/schemas/Format"
      - type: object
        properties:
          run_submission_wh:
            type: string
            nullable: true
            description: The webhook URL to send Discord embed-like information about completion submissions.
          map_submission_wh:
            type: string
            nullable: true
            description: The webhook URL to send Discord embed-like information about map submissions.
          emoji:
            type: string
            nullable: true
            description: A Discord emoji.
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
        proposed_values = None
        if self.id in src.utils.formats.formatinfo.format_info and \
                isinstance(src.utils.formats.formatinfo.format_info[self.id].proposed_values, tuple):
            proposed_values = src.utils.formats.formatinfo.format_info[self.id].proposed_values[1]
        return {
            "id": self.id,
            "name": self.name,
            "hidden": self.hidden,
            "run_submission_status": submission_status_to_str.get(self.run_submission_status, "closed"),
            "map_submission_status": submission_status_to_str.get(self.map_submission_status, "closed"),
            "proposed_difficulties": proposed_values,
        }

    def to_full_dict(self) -> dict:
        return {
            **self.to_dict(),
            "map_submission_wh": self.map_submission_wh,
            "run_submission_wh": self.run_submission_wh,
            "emoji": self.emoji,
        }
