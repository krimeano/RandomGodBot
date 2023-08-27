from models import Base as BaseObj
from models import engine as base_engine
from models import session


class DataBase:
    def select_all(self, model, **filter_s):
        query = session.query(model)
        if len(filter_s) > 0:
            query = query.filter_by(**filter_s)
        return query.all()

    def get_one(self, model, **filter_s):
        query = session.query(model)
        if len(filter_s) > 0:
            query = query.filter_by(**filter_s)
        return query.first()

    def test(self, model, **filter_s):
        if self.get_one(model, **filter_s):
            return True
        else:
            return False

    def new(self, model, *args):
        tmp_new = model(*args)
        session.add(tmp_new)
        session.commit()
        return tmp_new

    def delete(self, model, **filter_s):
        obj = self.select_all(model, **filter_s)
        if obj:
            for i in obj:
                session.delete(i)
            session.commit()
            return True
        else:
            return False

    def update(self, model, set, **filter_s):
        query = session.query(model)
        if len(filter_s) > 0:
            query = query.filter_by(**filter_s)
        query.update(set)
        session.commit()
        return True

    def set_state(self, model, *args):
        to_byte = model(*args)
        session.add(to_byte)
        session.commit()

    def base_init(self):
        BaseObj.metadata.create_all(base_engine)


d = DataBase()
d.base_init()
print('ok')
