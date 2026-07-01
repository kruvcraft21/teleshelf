from aiogram.filters.callback_data import CallbackData

class Pagination(CallbackData, prefix='pg'):
    current_page: int
    next_step: int

class TopicsPagination(Pagination, prefix='tpg'):
    pass

class FilesPagination(Pagination, prefix='fpg'):
    topic_id: int

if __name__ == '__main__':
    print(TopicsPagination(current_page=0, next_step=0).pack())
    print(FilesPagination(current_page=0, next_step=0, topic_id=0).pack())
    def test(p: Pagination):
        print(p.pack())

    test(TopicsPagination(current_page=0, next_step=0))