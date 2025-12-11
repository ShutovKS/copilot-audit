from src.app.services.code_analysis.parsers.python import FastAPIParser


def test_parse_fastapi_simple():
    # Using single quotes for the outer string to allow triple quotes inside
    code = '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    """Get an item by ID"""
    return {"item_id": item_id}

@app.post("/items")
def create_item(item: Item):
    pass
'''

    parser = FastAPIParser()
    endpoints = parser.parse_file("main.py", code)

    assert len(endpoints) == 2

    get_ep = endpoints[0]
    assert get_ep.method == "get"
    assert get_ep.path == "/items/{item_id}"
    assert get_ep.description == "Get an item by ID"
    assert len(get_ep.parameters) == 2
    assert get_ep.parameters[0].name == "item_id"
    assert get_ep.parameters[0].type_hint == "int"

    post_ep = endpoints[1]
    assert post_ep.method == "post"
    assert post_ep.parameters[0].name == "item"
