import logging
from abc import ABC, abstractmethod


class Patch(ABC):

    def __init__(self, debug=False):
        if debug:
            level = logging.DEBUG
        else:
            level = logging.INFO
        logging.basicConfig(level=level)
        self.logger = logging.getLogger(type(self).__name__)

        # Dict used for local storage
        self._local_storage = {}

    def log(self, msg):
        '''
            Log a message with the info log level, which is the default for troi. 

            :param msg: The message to log.
        '''
        self.logger.info(msg)

    def debug(self, msg):
        '''
            Log a message with debug log level. These messages will only be shown when debugging is enabled.
        '''
        self.logger.debug(msg)

    @property
    def local_storage(self):
        """
            Local storage for a patch. At times some elements in the pipeline will determine data that is needed
            name a playlist (and other situations). But without patch local storage, there is no way to pass this
            information to a later stage in the pipeline.
        """
        return self._local_storage

    @staticmethod
    def inputs():
        """
            This function should return a list of dicts that defined the type (argument or option), args, and kwargs to be passed to the click function. MusicBrainz entities and python base types can all be used. The documentation of the method is used as the help returned by the command. Example:

            .. code-block:: json

                [
                    {
                        "type" : "argument",
                        "args": ["num_recordings"],
                        "kwargs": {
                            "optional": true
                        }
                    }
                ]

        """
        return None

    @staticmethod
    def slug():
        ''' 
            Return the slug for this patch -- this is a URL friendly short identifier that can be used to invoke this patch via an HTTP call.

            e.g area-random-recordings
        '''

        return None

    @staticmethod
    def description():
        '''
            Return the description for this patch -- this short description (not more than a paragraph) should give the user an idea as to what the patch does.

            e.g "Generate a list of random recordings from a given area."
        '''

        return None

    @abstractmethod
    def create(self, input_args):
        """
            The function creates the data pipeline and then returns it. 

            Params:
               input_args: the arguments passed to the patch.
        """
        return None
