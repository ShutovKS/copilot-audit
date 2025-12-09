from src.app.services.code_analysis.parsers.js_ts import NodeJSParser

def test_parse_nestjs():
    code = """
    @Controller('cats')
    export class CatsController {
      @Post()
      create(@Body() createCatDto: CreateCatDto) {
        return 'This action adds a new cat';
      }

      @Get(':id')
      findOne(@Param('id') id: string) {
        return `This action returns a #${id} cat`;
      }
    }
    """
    
    parser = NodeJSParser()
    endpoints = parser.parse_file("cats.controller.ts", code)
    
    assert len(endpoints) == 2
    
    ep1 = endpoints[0]
    assert ep1.method == "post"
    assert ep1.path == "cats"
    assert ep1.function_name == "create"
    
    ep2 = endpoints[1]
    assert ep2.method == "get"
    assert ep2.path == "cats/:id"
    assert ep2.function_name == "findOne"

def test_parse_express():
    code = """
    const express = require('express')
    const app = express()
    
    app.get('/', (req, res) => {
      res.send('Hello World!')
    })
    
    app.post('/user', (req, res) => {
      res.send('Got a POST request')
    })
    """
    
    parser = NodeJSParser()
    endpoints = parser.parse_file("server.js", code)
    
    assert len(endpoints) == 2
    
    ep1 = endpoints[0]
    assert ep1.method == "get"
    assert ep1.path == "/"
    
    ep2 = endpoints[1]
    assert ep2.method == "post"
    assert ep2.path == "/user"
