import aiohttp_jinja2
from aiohttp import web
import jinja2

def make_routes(scheduler, event_log, workers, databases):
    routes = web.RouteTableDef()

    def basic_info():
        return {'workers': workers, 'databases': databases,
                'scheduler': scheduler, 'event_log': event_log}

    @routes.get('/')
    @aiohttp_jinja2.template('dashboard.html')
    async def dashboard(request):
        return { **basic_info() }

    # Build reports pages:

    @routes.get('/status/queue')
    @aiohttp_jinja2.template('queue.html')
    async def queue(request):
        return { **basic_info() }

    @routes.get('/status/completed')
    @aiohttp_jinja2.template('completed.html')
    async def completed(request):
        return { **basic_info() }

    @routes.get('/status/failed')
    @aiohttp_jinja2.template('failed.html')
    async def failed(request):
        return { **basic_info() }

    # Builds pages:

    # Package pages (by tag):

    # Database pages:


    # Worker pages:

    return routes

def make_app(*args, **kwargs):

    app = web.Application()
    app.router.add_static('/static/', path='static', 
            show_index=True, follow_symlinks=True, name='static')
    app.router.add_routes(make_routes(*args, **kwargs))

    # setup jinja template engine
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))
    return app
