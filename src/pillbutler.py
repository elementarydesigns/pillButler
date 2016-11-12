from __future__ import print_function
import logging,time
import boto3
import botocore
import json
import decimal
import sys
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from datetime import date


days_of_week=["MONDAY","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY","SATURDAY","SUNDAY"]


"""
use cases needed
#before prompting for remove or add, check if it exists

"""
# --------------START: Library functions for logging and DB access ------------------

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('PillButler')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def my_logging_handler(event, context):
    logger.info('got event{}'.format(event))
    logger.error('something went wrong')
    #return 'Hello World!'  
    

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Take care and be happpy. " \
                    "Have a nice day! "
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def add_medicine(intent,user,day_of_week,med):
    print("About to add medicine!!")
    
    #if no, create the first schedule with provided inputs
    all_meds=get_all_meds_json(intent,user) #internal client
    
    print ("This is what we found->",all_meds)
    
    #check if something exists for the user at all
    if ("Item" in all_meds and "info" in all_meds['Item']):
        #something exists
        #call to update
        print ("Something exists!")
        if day_of_week in all_meds['Item']['info']:
            #day of week exists
            #need to append
            print ("Something exists for the day!")
            days_meds=all_meds['Item']['info'][day_of_week]
            
            days_meds.add(med)
        else:
            print ("Nothing exists for the day!")
            days_meds={med}
            
        response = table.update_item(
            Key={
                "name":user
            },
            UpdateExpression="set info."+day_of_week+" = :v",
            ExpressionAttributeValues={
                ':v': days_meds
            },
            ReturnValues="UPDATED_NEW"
        )
        
    else:
        print("Nothing exists have to create new!")
        response = table.put_item(
            Item={
                "name":user,
                'info': {
                    day_of_week:{med}
                }
            }
        )
    
        
    print("UpdateItem succeeded:")
    #print(json.dumps(response, indent=4, cls=DecimalEncoder))

    session_attributes = {}
    reprompt_text = None
    print ("Added medication!!")
    
    speech_output = "I have added " + med + \
                        " to your "+ day_of_week +" schedule. What would you like to do next?"
    should_end_session = False

    # Setting reprompt_text to None signifies that we do not want to reprompt
    # the user. If the user does not respond or says something that is not
    # understood, the session will end.
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def remove_medicine(intent,user,day_of_week,med):
    meds_for_the_day=get_days_med_json(user,day_of_week)
    
    print ("meds for the day->",meds_for_the_day,". Going to remove ",med, " from ",day_of_week," schedule" )

    if med in meds_for_the_day:
        meds_for_the_day.remove(med)
    else:
        return get_welcome_response("I could not find the medicine in your "+day_of_week+" schedule. Please add it before attempting to remove it.")
    
    print ("meds for the day after removal->",meds_for_the_day)
    

    print ("Removing from existing set")
    response = table.update_item(
        Key={
            "name":user
        },
        UpdateExpression="DELETE info."+day_of_week+"  :v ",  
            ExpressionAttributeValues={
                ':v': {med}
        } ,
        ReturnValues="UPDATED_NEW"
    )
        
        
    print (meds_for_the_day)

    session_attributes = {}
    reprompt_text = None
    print ("Removed medication!!")
    
    speech_output = "I have removed " + med + \
                        " from your "+ day_of_week +" schedule. What would you like to do next?"
    should_end_session = False

    # Setting reprompt_text to None signifies that we do not want to reprompt
    # the user. If the user does not respond or says something that is not
    # understood, the session will end.
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def get_all_meds_json(intent,user):
    try:
        response = table.get_item(
            Key={
                'name': user
            }
        )
        print("GET_ALL_MEDS:", response)
        return response
    except ClientError as e:
        print(e.response['Error']['Message'])
        return null
    else:
        print("GetItem succeeded:")
        return response

def get_all_meds(intent,user):

    response=get_all_meds_json(intent,user)
    session_attributes = {}
    reprompt_text = None
     	
    speech_output="Here are your medications."
            

    if "info" in response['Item']:
       	    for d in days_of_week:
       	        print("Probing for ",d)
       	        if d in response['Item']['info']:
       	            speech_output+=" For "+d+", you have "
       	            for m in response['Item']['info'][d]:
       	                speech_output+=m+","
                
    else:
       	    speech_output="You have not entered your medications.Please add your schedule for each day."
        
    
    should_end_session = False

    # Setting reprompt_text to None signifies that we do not want to reprompt
    # the user. If the user does not respond or says something that is not
    # understood, the session will end.
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))


def get_days_med_json(user,day_of_week):
    all_meds = get_all_meds_json(None, user)

    print("Get days med:", all_meds)
    days_meds = []
    if "Item" in all_meds and "info" in all_meds['Item']:
        if day_of_week in all_meds['Item']['info']:
            days_meds = all_meds['Item']['info'][day_of_week]
            print("Meds for ", day_of_week, " ", days_meds)
            # return days_meds
        else:
            print("No meds for ", day_of_week)
            days_meds = []
    else:
        days_meds=[]

    return days_meds

def get_days_med(intent,user,day_of_week):
    all_meds=get_all_meds_json(None,user)
    
    print("Get days med:",all_meds)
    days_meds=[]
    if "info" in all_meds['Item']:
        if day_of_week in all_meds['Item']['info']:
            days_meds=all_meds['Item']['info'][day_of_week]
            print ("Meds for ",day_of_week," ",days_meds)
            #return days_meds
        else:
            print ("No meds for ",day_of_week)
    	    days_meds=[]

	session_attributes = {}
	reprompt_text = None

	speech_output="You take "

	#print ("In get all meds->",response)

	if len(days_meds)>0:
		speech_output="You take "
		for m in days_meds:
			speech_output+=m+","
		speech_output+=" on "+day_of_week+"s."

	else:
	    speech_output="You have not entered your medications for "+day_of_week+". Please add your schedule for "+day_of_week+"s."


	should_end_session = False

	# Setting reprompt_text to None signifies that we do not want to reprompt
	# the user. If the user does not respond or says something that is not
	# understood, the session will end.
	return build_response(session_attributes, build_speechlet_response(
	    intent['name'], speech_output, reprompt_text, should_end_session))


def remove_all_meds(intent, user):
    try:
        response = table.delete_item(
            Key={
                'name': user
                }
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("DeleteItem succeeded:")


        session_attributes = {}
        reprompt_text = "I am sorry. What would you like to do next?"
        print("Removed medication!!")

        speech_output = "I have removed all your medications."  + \
                "What would you like to do next?"
        should_end_session = False

        # Setting reprompt_text to None signifies that we do not want to reprompt
        # the user. If the user does not respond or says something that is not
        # understood, the session will end.
        return build_response(session_attributes, build_speechlet_response(
            intent['name'], speech_output, reprompt_text, should_end_session))



def add_medicine_confirm(intent,user,day_of_week,med):
    session_attributes = {"ACTION":"ADD_MED","USER":user,"DAY_OF_WEEK":day_of_week,"MED":med}
    reprompt_text = None
    print ("In add_medicine_confirm: seeking confirmation to add with session populated!")
    
    speech_output = "Are you sure you want to add " + med + \
                        " to your "+ day_of_week +" schedule?"
    should_end_session = False

    # Setting reprompt_text to None signifies that we do not want to reprompt
    # the user. If the user does not respond or says something that is not
    # understood, the session will end.
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))
        
def remove_med_confirm(intent,user,day_of_week,med):
    session_attributes = {"ACTION":"REMOVE_MED","USER":user,"DAY_OF_WEEK":day_of_week,"MED":med}
    reprompt_text = None
    print ("In remove_med_confirm: seeking confirmation with session populated!")
    
    speech_output = "Are you sure you want to remove " + med + \
                        " from your "+ day_of_week +" schedule?"
    should_end_session = False

    # Setting reprompt_text to None signifies that we do not want to reprompt
    # the user. If the user does not respond or says something that is not
    # understood, the session will end.
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))


def remove_all_meds_conf(intent, user):
    session_attributes = {"ACTION": "REMOVE_ALL_MEDS", "USER": user}
    reprompt_text = None
    print("In remove_med_confirm: seeking confirmation with session populated!")

    speech_output = "Are you sure you want to remove all meds from your schedule?"
    should_end_session = False
    reprompt_text="I am sorry - what was that again?"

    # Setting reprompt_text to None signifies that we do not want to reprompt
    # the user. If the user does not respond or says something that is not
    # understood, the session will end.
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))



def process_yes_no_intent(intent,session):
    session_attributes = {}
    reprompt_text = None
    print ("In yes-no-intent processing with intent=",intent)
    intent_name = intent['name']
    print ("In process yes/no:",session," with ",intent_name)

    if not session.get('attributes', {}):
        return get_welcome_response()

    if session.get('attributes', {}):
        if "ACTION" in session.get('attributes', {}):
            action=session['attributes']['ACTION']
            print ("Action->",action)
        if "MED" in session.get('attributes', {}):
            med=session['attributes']['MED']
            print ("Medicine->",med)
        if "DAY_OF_WEEK" in session.get('attributes', {}):
            day_of_week=session['attributes']['DAY_OF_WEEK']
            print ("Day of week->",day_of_week)
        if "USER" in session.get('attributes', {}):
            user=session['attributes']['USER']
            print ("User->",user)            
    
    if intent_name == "AMAZON.YesIntent":
    	if action=="REMOVE_MED": # remove_medicine(user,day_of_week,med):
    	    return remove_medicine(intent,user,day_of_week,med)   
    	if action=="ADD_MED":
    	    print ("Got signal to ADD_MED!")
    	    return add_medicine(intent,user,day_of_week,med)
    	if action=="REMOVE_ALL_MEDS":
    	    print ("Got signal to remove all meds")
    	    return remove_all_meds(intent, user)
    elif intent_name == "AMAZON.NoIntent":
    	if action=="REMOVE_MED": # remove_medicine(user,day_of_week,med):
    	    return get_welcome_response("Ceasing and desisting from removing "+ med+ " from your "+day_of_week+ " schedule.")
    	if action=="ADD_MED":
    	    print ("Got signal to ADD_MED!")
    	    return get_welcome_response("Ceasing and desisting from adding "+ med+ " to your "+day_of_week+ " schedule.")
    	if action=="REMOVE_ALL_MEDS":
    	    print ("Got signal to remove med")
    	    return get_welcome_response("Ceasing and desisting from removing all your meds")
    else:
        return get_welcome_response("I am sorry. What would you like to do?")
    


    
# --------------- Helpers that build all of the responses ----------------------


def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': "SessionSpeechlet - " + title,
            'content': "SessionSpeechlet - " + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------
def get_welcome_response(msg=None):
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    session_attributes = {}
    card_title = "Welcome"
    if msg==None:
        speech_output = "Welcome to the your pill butler. " \
                        "I can help you with your pill schedule. " \
                        "Go ahead and ask me about your pills. "
    else:
        speech_output=msg

    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "Sorry - I didn't quite understand.  " + speech_output
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))



# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])

def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()

def on_intent(intent_request, session,user):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']
    print ('Intent name:',intent_name)
    print ('Intent request:',intent_request)
    

    if ("slots" in  intent_request['intent']):
        if ("day" in intent_request['intent']['slots']):
            day_of_week =(intent_request['intent']['slots']['day']['value']).upper()
            print ("Day of week requested",day_of_week)
            if (day_of_week not in days_of_week):
                print("HOUSTON! WE HAVE A PROBLEM! USER CALLING FROM A DIFFERENT PLANET!")
                return get_welcome_response("I cannot work with that day. Please use a valid day of the week.")
        else:
            print ('Day of week not found!')
        
        if ("med" in intent_request['intent']['slots']):
            med=intent_request['intent']['slots']['med']['value']
            print('Med=',med)
        else:
            print ('Med not found!')
    
    # Dispatch to your skill's intent handlers
    if intent_name == "AddMedIntent":
        print('Calling AddMedIntent handler!')
        #return add_medicine(user,day_of_week,med)
        return add_medicine_confirm(intent,user,day_of_week,med)        
    elif intent_name == "RemoveMedIntent":
        print('Calling RemoveMedIntent handler!')
    	#return remove_medicine(user,day_of_week,med)
    	return remove_med_confirm(intent,user,day_of_week,med)
    elif intent_name == "ListAllMedsIntent":
        print ('Calling ListAllMedsIntent handler!')
    	return get_all_meds(intent,user) #external client to return to FE
    elif intent_name == "ListMedsForTodayIntent":
        day_of_week=date.today().strftime("%A").upper()
        print ('Calling ListMedsForTodayIntent handler!')
    	return get_days_med(intent,user,day_of_week)#external client to return to FE
    elif intent_name == 'ListDayMedsIntent':
    	print ('Calling ListDayMedsIntent handler!')
    	return get_days_med(intent,user,day_of_week)
    elif intent_name == 'RemoveAllMedsIntent':
        print ('Calling RemoveAllMedsIntent handler!')
    	return remove_all_meds_conf(intent,user)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    elif intent_name == "AMAZON.YesIntent" or intent_name == "AMAZON.NoIntent":
        return process_yes_no_intent(intent,session)
    else:
        raise ValueError("Invalid intent")
        
    return get_welcome_response()

def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here



# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
    #     raise ValueError("Invalid Application ID")

    for a in event:
        print ("PRINTING EVENTS NOW!")
        print (a)
        print (event[a])
    
    print ('User:**>',event['session']['user']['userId'])
    
    user=event['session']['user']['userId']
    
    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'],user)
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])
