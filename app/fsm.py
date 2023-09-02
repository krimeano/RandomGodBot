import pickle

import models


class FSM:
    def __init__(self, base):
        self.base = base

    def set_state(self, user_id, state, **arg):
        self.base.delete(models.State, user_id=user_id)
        data = pickle.dumps(arg)
        self.base.set_state(models.State, user_id, state, data)

    def get_state(self, user_id):
        tmp = self.base.select_all(models.State, user_id=user_id)
        if tmp:
            arg = pickle.loads(tmp[0].arg)
            return tmp[0].state, arg
        else:
            return "idle", []

    def get_state_key(self, user_id):
        return self.get_state(user_id)[0]

    def get_state_arg(self, user_id):
        return self.get_state(user_id)[1]
