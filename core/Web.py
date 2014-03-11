from twisted.web import static, server, resource, util
import md5, base64

class Web(resource.Resource):
    def __init__(self, cfg):
        resource.Resource.__init__(self)

        self.baseurl = cfg.get('Web', 'baseurl')
        self.putChild('', self)
        self.putChild('css', static.File('./css/'))

        self.urlstorage = URLStorage(self.baseurl)
        self.putChild('u', self.urlstorage)

class URLStorage(resource.Resource):
    def __init__(self, baseurl):
        resource.Resource.__init__(self)
        self.baseurl = baseurl
        self.urls = {}

    def getChild(self, path, request):
        if path not in self.urls:
            return NotFound()
        return RedirectURL(self.urls[path])

    def addURL(self, url):
        key = base64.b32encode(md5.md5(url).hexdigest())[0:8].lower()
        self.urls[key] = str(url)
        return '%s/u/%s' % (self.baseurl, key)

class RedirectURL(resource.Resource):
    def __init__(self, url):
        resource.Resource.__init__(self)
        self.url = url

    def render(self, request):
        request.redirect(self.url)
        request.finish()
        return ''

class NotFound(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)

    def render(self, request):
        request.setResponseCode(404)
        return '404 Not found :D'

class GenPage(resource.Resource):
    def __init__(self, code):
        resource.Resource.__init__(self)
        self.code = code

    def render(self, request):
        return self.code
