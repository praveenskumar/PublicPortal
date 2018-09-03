from flask_cache import Cache

cache = Cache()


class CacheHelper(object):
    def get_clients_allowed_key(self, vendor_id):
        return 'clients_allowed-%s' % vendor_id


cache_helper = CacheHelper()
