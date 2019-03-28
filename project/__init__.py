from flask import Flask

def create_app():
    from project.main_module import routes

    app = Flask(__name__)
    app.config.from_object('project.settings')

    routes.init_app(app)

    return app
