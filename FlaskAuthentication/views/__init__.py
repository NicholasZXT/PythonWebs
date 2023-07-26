from .views1 import *

@bp1.route("/", methods=['GET'])
def hello():
    return "<h1>Hello Flask for Authentication !</h1>"

