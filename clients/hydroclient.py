from hydrogram import Client

class HydroClient(Client):
    @classmethod
    async def start(cls, **kwargs):
        self = HydroClient(**kwargs)
        await super(HydroClient, self).start()
        return self
