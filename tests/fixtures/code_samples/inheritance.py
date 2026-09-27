class Base:
    def run(self):
        pass


class Derived(Base):
    def run(self):
        super().run()
