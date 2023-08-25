import datetime
import cloudlanguagetools.constants
import cloudlanguagetools.languages

PATREON_MONTHLY_CHARACTER_LIMIT = 250000

TRIAL_USER_CHARACTER_LIMIT = 5000
TRIAL_EXTENDED_USER_CHARACTER_LIMIT = 50000
TRIAL_VIP_USER_CHARACTER_LIMIT = 100000

EASYPRONUNCIATION_USER_DAILY_MAX_CHARACTERS = 136000

FORVO_USER_DAILY_MAX_REQUESTS = 7000

GETCHEDDAR_CHAR_MULTIPLIER = 1000.0
# no plan is greater than 2m/month
GETCHEDDAR_MONTHLY_MAX_CHAR = 2000000

AZURE_CJK_CHAR_MULTIPLIER = 2
NAVER_AUDIO_CHAR_MULTIPLIER = 6
ELEVENLABS_AUDIO_CHAR_MULTIPLIER = 15

BREAKDOWN_CHAR_MULTIPLIER = 3

COST_TABLE = [
    # audio
    {
        'service': 'Azure',
        'request_type': 'audio',
        'character_cost': (1.0/1000000) * 16 * 1.255
    },
    {
        'service': 'Google',
        'request_type': 'audio',
        'character_cost': (1.0/1000000) * 16
    },
    {
        'service': 'Amazon',
        'request_type': 'audio',
        'character_cost': (1.0/1000000) * 16
    },                        
    {
        'service': 'Watson',
        'request_type': 'audio',
        'character_cost': (1.0/1000) * 0.02
    },
    {
        'service': 'Naver',
        'request_type': 'audio',
        'character_cost': ((1.0/1000) * 0.090) / NAVER_AUDIO_CHAR_MULTIPLIER
    },
    {
        'service': cloudlanguagetools.constants.Service.ElevenLabs.name,
        'request_type': cloudlanguagetools.constants.RequestType.audio.name,
        'character_cost': ((1.0/1000) * 0.30) / ELEVENLABS_AUDIO_CHAR_MULTIPLIER
    },    
    {
        'service': cloudlanguagetools.constants.Service.CereProc.name,
        'request_type': cloudlanguagetools.constants.RequestType.audio.name,
        'character_cost': ((1.0/1000000) * 16.31)
    },
    {
        'service': cloudlanguagetools.constants.Service.FptAi.name,
        'request_type': cloudlanguagetools.constants.RequestType.audio.name,
        'character_cost': ((1.0/1500000) * 21.28)
    },        
    # translation
    {
        'service': 'Azure',
        'request_type': 'translation',
        'character_cost': (1.0/1000000) * 10
    },
    {
        'service': 'Google',
        'request_type': 'translation',
        'character_cost': (1.0/1000000) * 20
    },
    {
        'service': 'Amazon',
        'request_type': 'translation',
        'character_cost': (1.0/1000000) * 15
    },            
    {
        'service': 'Watson',
        'request_type': 'translation',
        'character_cost': (1.0/1000) * 0.02
    },            
    {
        'service': 'Naver',
        'request_type': 'translation',
        'character_cost': (1.0/1000000) * 17.70
    },            
    {
        'service': 'DeepL',
        'request_type': 'translation',
        'character_cost': (1.0/1000000) * 24.22
    },
    # transliteration
    {
        'service': 'Azure',
        'request_type': 'transliteration',
        'character_cost': (1.0/1000000) * 10
    },            

]

def adjust_character_count(
    service: cloudlanguagetools.constants.Service, 
    request_type: cloudlanguagetools.constants.RequestType,
    language: cloudlanguagetools.languages.Language,
    characters: int):
    
    azure_double_count_languages = [
            cloudlanguagetools.languages.Language.ja,
            cloudlanguagetools.languages.Language.ko,
            cloudlanguagetools.languages.Language.yue,
            cloudlanguagetools.languages.Language.zh_cn,
            cloudlanguagetools.languages.Language.zh_tw
        ]

    if request_type == cloudlanguagetools.constants.RequestType.breakdown:  
        return characters * BREAKDOWN_CHAR_MULTIPLIER

    if language != None:
        if language in azure_double_count_languages:
            if service == cloudlanguagetools.constants.Service.Azure:
                if request_type == cloudlanguagetools.constants.RequestType.audio:
                    return characters * AZURE_CJK_CHAR_MULTIPLIER

    if service == cloudlanguagetools.constants.Service.Naver:
        if request_type == cloudlanguagetools.constants.RequestType.audio:
            return characters * NAVER_AUDIO_CHAR_MULTIPLIER

    if service == cloudlanguagetools.constants.Service.ElevenLabs:
        if request_type == cloudlanguagetools.constants.RequestType.audio:
            return characters * ELEVENLABS_AUDIO_CHAR_MULTIPLIER

    return characters

class UsageSlice():
    def __init__(self, 
                request_type: cloudlanguagetools.constants.RequestType, 
                usage_scope: cloudlanguagetools.constants.UsageScope, 
                usage_period: cloudlanguagetools.constants.UsagePeriod, 
                service: cloudlanguagetools.constants.Service, 
                api_key: str,
                api_key_type: cloudlanguagetools.constants.ApiKeyType,
                api_key_data):
        self.request_type = request_type
        self.usage_scope = usage_scope
        self.usage_period = usage_period
        self.service = service
        self.api_key = api_key
        self.api_key_type = api_key_type
        self.api_key_data = api_key_data

    def build_key_suffix(self) -> str:
        if self.usage_scope == cloudlanguagetools.constants.UsageScope.User and self.usage_period == cloudlanguagetools.constants.UsagePeriod.recurring:
            return f'{self.usage_scope.key_str}:{self.usage_period.name}:{self.api_key}'

        if self.usage_scope == cloudlanguagetools.constants.UsageScope.User and self.usage_period == cloudlanguagetools.constants.UsagePeriod.lifetime:
            return f'{self.usage_scope.key_str}:{self.usage_period.name}:{self.api_key}'

        date_str = datetime.datetime.today().strftime('%Y%m')
        if self.usage_period == cloudlanguagetools.constants.UsagePeriod.daily:
            date_str = datetime.datetime.today().strftime('%Y%m%d')

        api_key_suffix = ''
        if self.usage_scope == cloudlanguagetools.constants.UsageScope.User:
            api_key_suffix = f':{self.api_key}'

        if self.usage_scope == cloudlanguagetools.constants.UsageScope.User and self.usage_period == cloudlanguagetools.constants.UsagePeriod.patreon_monthly:
            return f'{self.usage_scope.key_str}:{self.usage_period.name}:{date_str}{api_key_suffix}'

        return f'{self.usage_scope.key_str}:{self.usage_period.name}:{date_str}:{self.service.name}:{self.request_type.name}{api_key_suffix}'


    def over_quota(self, characters, requests) -> bool:
        # some services have daily restrictions
        if self.usage_scope == cloudlanguagetools.constants.UsageScope.User:
            if self.usage_period == cloudlanguagetools.constants.UsagePeriod.daily:
                if self.service == cloudlanguagetools.constants.Service.EasyPronunciation:
                    if characters > EASYPRONUNCIATION_USER_DAILY_MAX_CHARACTERS:
                        return True
                if self.service == cloudlanguagetools.constants.Service.Forvo:
                    if requests > FORVO_USER_DAILY_MAX_REQUESTS:
                        return True

        # print(f'over_quota: usage_period: {self.usage_period} api_key_type: {self.api_key_type}')
        if self.api_key_type == cloudlanguagetools.constants.ApiKeyType.getcheddar:
            if self.usage_scope == cloudlanguagetools.constants.UsageScope.User:
                if self.usage_period == cloudlanguagetools.constants.UsagePeriod.monthly:
                    if characters > GETCHEDDAR_MONTHLY_MAX_CHAR:
                        return True

            if self.usage_period == cloudlanguagetools.constants.UsagePeriod.recurring:
                if self.api_key_data['thousand_char_overage_allowed'] == 1:
                    # overages allowed, don't restrict
                    return False
                total_chars = GETCHEDDAR_CHAR_MULTIPLIER * self.api_key_data['thousand_char_used'] + characters
                allowed_chars = GETCHEDDAR_CHAR_MULTIPLIER * self.api_key_data['thousand_char_quota']
                # print(f'total_chars: {total_chars} allowed_chars: {allowed_chars}')
                if total_chars > allowed_chars:
                    return True
            # don't run through other checks for getcheddar users
            return False

        if self.api_key_type == cloudlanguagetools.constants.ApiKeyType.patreon:
            if self.usage_period == cloudlanguagetools.constants.UsagePeriod.patreon_monthly:
                if characters > PATREON_MONTHLY_CHARACTER_LIMIT:
                    return True
            # don't run through other checks for patreon users
            return False

        if self.usage_scope == cloudlanguagetools.constants.UsageScope.User:
            if self.usage_period == cloudlanguagetools.constants.UsagePeriod.lifetime:
                character_limit = self.api_key_data.get('character_limit', None)
                if character_limit != None:
                    if characters > character_limit:
                        return True

        return False


