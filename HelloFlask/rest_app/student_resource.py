from flask import Blueprint, request
from flask_restful import Api, Resource, reqparse, fields, marshal_with


# 模拟数据
STUDENTS = {
    'ming': {}
}


rest_bp = Blueprint('rest', __name__)
api = Api(rest_bp)

parser = reqparse.RequestParser()
parser.add_argument('rate', type=int, help='Rate cannot be converted')
parser.add_argument('name')
args = parser.parse_args()


student_fields = {
    'name': fields.String,
    'age': fields.Integer,
    'birthday': fields.DateTime,
    'address': fields.Nested({
        'province': fields.String,
        'city': fields.String
    })
}


class Student(Resource):
    def get(self):
        pass

    def put(self):
        pass

    def post(self):
        pass

    def delete(self):
        pass

api.add_resource(Student, '/students')

