from watson_developer_cloud import ConversationV1 as CV1


class Conversation_Service:
    """Conversation Service class.

    Define a class for communication initated with settings dictionary with
    keys: 'username', 'password', 'version', 'workspace_id'
    """

    def __init__(self, settings=None):
        """Check if settings where delivered."""
        if settings is None:
            # TODO throw error
            pass

        # store settings
        self.settings = settings

        # init conversation API
        self.conversation = CV1(
            username=settings['username'],
            password=settings['password'],
            version=settings['version'],
        )

    # request function
    def talk(self, input_txt, context):
        """Request."""
        response = self.conversation.message(
            workspace_id=self.settings['workspace_id'],
            context=context, message_input={'text': input_txt})

        # parse answer:

        # default cases
        response_text = '[-]NO_TEXT_SUPPLIED'
        response_intents = '[-]NO_INTENTS'
        response_entities = '[-]NO_ENTITIES'

        # TODO How and why does this work?
        if response['output']['text']:
            response_text = response['output']['text'][0]
        if response['intents']:
            response_intents = response['intents'][0]['intent']
        response_entities = [entity for entity in response['entities']]

        # NOTE: We update "context" in this function automatically
        # TODO: Why like this? Maybe call by reference?
        context.clear()
        context.update(response['context'])

        return response_text, response_intents, response_entities

    # for starting a new conversation and creating a context var
    def conversation_init(self):
        """Create initial context."""
        context = dict()
        # send empty request to skip conversation starter TODO
        self.talk('', context)

        return context
