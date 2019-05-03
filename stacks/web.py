import aiohttp_jinja2
from aiohttp import web
import jinja2
import datetime

def make_routes(scheduler, event_log, workers, databases):
    routes = web.RouteTableDef()

    def basic_info():
        return {'time': datetime.datetime.now(),
                'workers': workers, 'databases': databases,
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

    @routes.get('/status/running')
    @aiohttp_jinja2.template('running.html')
    async def running(request):
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
    @routes.get('/build/{id}')
    @aiohttp_jinja2.template('build.html')
    async def build(request):
        try:
            id = int(request.match_info['id'])
            build = event_log.get_build_by_id(id)
            if not build:
                raise web.HTTPNotFound()
            return { **basic_info(), 'build' : build }
        except ValueError:
            raise web.HTTPNotFound()

    # Package pages (by tag):
    @routes.get('/package/{tag}')
    async def package(request):
        tag = request.match_info['tag']
        raise web.HTTPFound('/tag/' + tag)

    @routes.get('/tag/{tag}')
    @aiohttp_jinja2.template('tag.html')
    async def tag(request):
        tag = request.match_info['tag']
        history = event_log.get_events_by_tag(tag)
        return { **basic_info(), 'tag' : tag, 'history': history}

    # Database pages:
    @routes.get('/database/{name}')
    @aiohttp_jinja2.template('database.html')
    async def database(request):
        name = request.match_info['name']
        database = None
        for db in databases:
            if db.name == name:
                database = db
                break
        if database is None:
            raise web.HTTPNotFound()

        return { **basic_info(), 'database' : database}

    # Worker pages:
    @routes.get('/worker/{name}')
    @aiohttp_jinja2.template('worker.html')
    async def database(request):
        name = request.match_info['name']
        worker = None
        for w in workers:
            if w.name == name:
                worker = w
                break
        if worker is None:
            raise web.HTTPNotFound()
        return { **basic_info(), 'worker' : worker}

    @aiohttp_jinja2.template('404.html')
    async def handle(request):
        return { **basic_info() }

    return routes

def make_app(*args, **kwargs):

    app = web.Application()
    app.router.add_static('/static/', path='static', 
            show_index=True, follow_symlinks=True, name='static')
    app.router.add_routes(make_routes(*args, **kwargs))

    # setup jinja template engine
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))
    return app
