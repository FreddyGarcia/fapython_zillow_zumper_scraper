from flask import Blueprint, redirect, jsonify, request, render_template, flash, g, send_file

routes = Blueprint('routes', __name__, url_prefix='/')

@routes.route("")
def index():
    return '', 200

def init_app(app):
    app.register_blueprint(routes)
