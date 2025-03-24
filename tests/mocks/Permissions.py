

class Permissions:
    @staticmethod
    def basic() -> set[str]:
        return {
            "create:map_submission",
            "create:completion_submission",
        }

    @staticmethod
    def verifier() -> set[str]:
        return Permissions.basic().union({
            "edit:config",
            "create:completion",
            "edit:completion",
            "delete:completion",
        })

    @staticmethod
    def curator() -> set[str]:
        return Permissions.basic().union({
            "create:map",
            "edit:map",
            "delete:map",
        })

    @staticmethod
    def mod() -> set[str]:
        return Permissions.verifier().union(Permissions.curator())

    @staticmethod
    def requires_recording() -> set[str]:
        return {"require:completion_submission:recording"}
