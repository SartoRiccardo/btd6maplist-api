

class Permissions:
    class edit:
        config = "edit:config"
        map = "edit:map"
        completion = "edit:completion"
        achievement_roles = "edit:achievement_roles"
        self = "edit:self"

    class delete:
        map = "delete:map"
        completion = "delete:completion"
        map_submission = "delete:map_submission"

    class create:
        map = "create:map"
        user = "create:user"
        completion = "create:completion"
        map_submission = "create:map_submission"
        completion_submission = "create:completion_submission"

    class misc:
        ban_user = "ban:user"

    @staticmethod
    def basic() -> set[str]:
        return {
            Permissions.edit.self,
            Permissions.create.map_submission,
            Permissions.create.completion_submission,
        }

    @staticmethod
    def verifier() -> set[str]:
        return Permissions.basic().union({
            Permissions.create.user,
            Permissions.edit.config,
            Permissions.create.completion,
            Permissions.edit.completion,
            Permissions.delete.completion,
            Permissions.misc.ban_user,
            Permissions.edit.achievement_roles,
        })

    @staticmethod
    def curator() -> set[str]:
        return Permissions.basic().union({
            Permissions.create.user,
            Permissions.create.map,
            Permissions.edit.map,
            Permissions.delete.map,
            Permissions.delete.map_submission,
            Permissions.misc.ban_user,
            Permissions.delete.map_submission,
        })

    @staticmethod
    def mod() -> set[str]:
        return {
            Permissions.edit.achievement_roles
        }\
            .union(Permissions.verifier())\
            .union(Permissions.curator())

    @staticmethod
    def requires_recording() -> set[str]:
        return Permissions.basic().union({
            "require:completion_submission:recording"
        })
