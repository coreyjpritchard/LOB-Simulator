from lobsim.book import Book


def test_market_order_walks_the_book_in_price_time_order():
    book = Book()
    book.add_limit("sell", 10, 1.0)
    first = book.add_limit("sell", 11, 1.5)
    book.add_limit("sell", 11, 0.5)
    assert book.add_market("buy", 2.0) == 0.0
    assert book.best_ask() == 11
    assert book.orders[first].qty == 0.5
    book.add_limit("buy", 9, 1.0)
    assert book.spread() == 2


def test_cancel_removes_a_resting_order():
    book = Book()
    oid = book.add_limit("buy", 5, 1.0)
    assert book.cancel(oid)
    assert book.best_bid() is None
    assert book.cancel(oid) is False
