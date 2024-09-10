import time


def timed_function(refresh_time):
    def decorator(function):
        def wrapper(self, *args, **kwargs):
            current_time = time.time()
            if (current_time -
                    self._function_call_times.get(function.__name__, 0) >
                    refresh_time):
                function(self, *args, **kwargs)
                self._function_call_times[function.__name__] = current_time

        return wrapper
    return decorator


def statusbar_message(message):
    def decorator(function):
        def wrapper(self):
            self.ui.statusbar.showMessage(message)
            function(self)
            self.ui.statusbar.clearMessage()

        return wrapper
    return decorator