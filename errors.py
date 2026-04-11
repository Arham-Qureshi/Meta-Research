from flask import jsonify, request
import logging

log = logging.getLogger(__name__)

def api_success(data=None, message=None, status=200, **extras):
    body = {'success': True}
    if data is not None:
        body['data'] = data
    if message:
        body['message'] = message
    body.update(extras)
    return jsonify(body), status

def api_error(message, status=400, details=None):
    body = {'error': message}
    if details:
        body['details'] = details
    return jsonify(body), status

class APIError(Exception):
    status_code = 500
    message = 'Internal server error'

    def __init__(self, message=None, status_code=None, details=None):
        super().__init__(message or self.message)
        if message:
            self.message = message
        if status_code:
            self.status_code = status_code
        self.details = details

class ValidationError(APIError):
    status_code = 400
    message = 'Validation error'

class AuthenticationError(APIError):
    status_code = 401
    message = 'Authentication required'

class ForbiddenError(APIError):
    status_code = 403
    message = 'Access denied'

class NotFoundError(APIError):
    status_code = 404
    message = 'Resource not found'

class ConflictError(APIError):
    status_code = 409
    message = 'Resource already exists'

def _is_api_request():
    return (
        request.path.startswith('/api/')
        or request.content_type == 'application/json'
        or request.accept_mimetypes.best == 'application/json'
    )

def register_error_handlers(app):
    @app.errorhandler(APIError)
    def handle_api_error(exc):
        log.warning('APIError [%s]: %s', exc.status_code, exc.message)
        return api_error(exc.message, exc.status_code, exc.details)

    @app.errorhandler(400)
    def handle_400(exc):
        if _is_api_request():
            return api_error('Bad request', 400)
        return exc

    @app.errorhandler(401)
    def handle_401(exc):
        if _is_api_request():
            return api_error('Authentication required', 401)
        return exc

    @app.errorhandler(403)
    def handle_403(exc):
        if _is_api_request():
            return api_error('Access denied', 403)
        return exc

    @app.errorhandler(404)
    def handle_404(exc):
        if _is_api_request():
            return api_error('Not found', 404)
        return exc

    @app.errorhandler(405)
    def handle_405(exc):
        if _is_api_request():
            return api_error('Method not allowed', 405)
        return exc

    @app.errorhandler(409)
    def handle_409(exc):
        if _is_api_request():
            return api_error('Conflict', 409)
        return exc

    @app.errorhandler(413)
    def handle_413(exc):
        if _is_api_request():
            return api_error('Request payload too large. Maximum size is 2 MB.', 413)
        return exc

    @app.errorhandler(429)
    def handle_429(exc):
        if _is_api_request():
            return api_error('Too many requests. Please slow down.', 429)
        return exc

    @app.errorhandler(500)
    def handle_500(exc):
        log.exception('Unhandled server error')
        if _is_api_request():
            message = 'Internal server error'
            if app.debug:
                message = str(exc)
            return api_error(message, 500)
        return exc
