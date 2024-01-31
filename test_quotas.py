import unittest
import quotas
import datetime

import cloudlanguagetools.constants
import cloudlanguagetools.languages

class TestQuotas(unittest.TestCase):

    def test_adjust_character_count(self):
        services = cloudlanguagetools.constants.Service
        request_type = cloudlanguagetools.constants.RequestType.audio
        languages = cloudlanguagetools.languages.Language
        self.assertEqual(quotas.adjust_character_count(services.Google, request_type, languages.en, 42), 42)
        self.assertEqual(quotas.adjust_character_count(services.Azure, request_type, languages.fr, 42), 42)
        self.assertEqual(quotas.adjust_character_count(services.Azure, request_type, None, 42), 42)
        self.assertEqual(quotas.adjust_character_count(services.Azure, request_type, languages.ja, 42), 84)
        self.assertEqual(quotas.adjust_character_count(services.Azure, request_type, languages.ko, 42), 84)
        self.assertEqual(quotas.adjust_character_count(services.Azure, request_type, languages.zh_cn, 42), 84)
        self.assertEqual(quotas.adjust_character_count(services.Azure, request_type, languages.zh_tw, 42), 84)
        self.assertEqual(quotas.adjust_character_count(services.Azure, request_type, languages.yue, 42), 84)

        self.assertEqual(quotas.adjust_character_count(services.Naver, request_type, languages.ja, 10), 60)
        self.assertEqual(quotas.adjust_character_count(services.ElevenLabs, request_type, languages.en, 10), 150)
        self.assertEqual(quotas.adjust_character_count(services.OpenAI, request_type, languages.en, 10), 20)

    def test_quotas_getcheddar(self):
        usage_slice = quotas.UsageSlice(
            None,
            cloudlanguagetools.constants.UsageScope.User, 
            cloudlanguagetools.constants.UsagePeriod.recurring,
            None,
            'getcheddar_api_key_1',
            cloudlanguagetools.constants.ApiKeyType.getcheddar,
            {'thousand_char_quota': 250,
            'thousand_char_overage_allowed': 0,
            'thousand_char_used': 0})

        self.assertEqual(usage_slice.over_quota(249000, 200), False)
        self.assertEqual(usage_slice.over_quota(250001, 200), True)

        usage_slice_existing_usage = quotas.UsageSlice(
            cloudlanguagetools.constants.RequestType.audio,
            cloudlanguagetools.constants.UsageScope.User, 
            cloudlanguagetools.constants.UsagePeriod.recurring,
            cloudlanguagetools.constants.Service.Azure,
            'getcheddar_api_key_1',
            cloudlanguagetools.constants.ApiKeyType.getcheddar,
            {'thousand_char_quota': 250,
            'thousand_char_overage_allowed': 0,
            'thousand_char_used': 240})

        self.assertEqual(usage_slice_existing_usage.over_quota(9000, 200), False)
        self.assertEqual(usage_slice_existing_usage.over_quota(11000, 200), True)

        usage_slice_overage_allowed = quotas.UsageSlice(
            cloudlanguagetools.constants.RequestType.audio,
            cloudlanguagetools.constants.UsageScope.User, 
            cloudlanguagetools.constants.UsagePeriod.recurring,
            cloudlanguagetools.constants.Service.Azure,
            'getcheddar_api_key_1',
            cloudlanguagetools.constants.ApiKeyType.getcheddar,
            {'thousand_char_quota': 500,
            'thousand_char_overage_allowed': 1,
            'thousand_char_used': 0})        

        self.assertEqual(usage_slice_overage_allowed.over_quota(500001, 200), False)

    def test_quotas_getcheddar_monthly_max(self):
        usage_slice = quotas.UsageSlice(
            None,
            cloudlanguagetools.constants.UsageScope.User, 
            cloudlanguagetools.constants.UsagePeriod.monthly,
            None,
            'getcheddar_api_key_1',
            cloudlanguagetools.constants.ApiKeyType.getcheddar,
            {'thousand_char_quota': 3000,
            'thousand_char_overage_allowed': 0,
            'thousand_char_used': 0})

        self.assertEqual(usage_slice.over_quota(1999999, 200), False)
        self.assertEqual(usage_slice.over_quota(2000001, 200), True)

        usage_slice = quotas.UsageSlice(
            None,
            cloudlanguagetools.constants.UsageScope.Global, 
            cloudlanguagetools.constants.UsagePeriod.monthly,
            None,
            'getcheddar_api_key_1',
            cloudlanguagetools.constants.ApiKeyType.getcheddar,
            {'thousand_char_quota': 3000,
            'thousand_char_overage_allowed': 0,
            'thousand_char_used': 0})

        self.assertEqual(usage_slice.over_quota(1999999, 200), False)
        self.assertEqual(usage_slice.over_quota(2000001, 200), False)



    def test_quotas_trial(self):
        usage_slice_monthly_global = quotas.UsageSlice(
            cloudlanguagetools.constants.RequestType.audio,
            cloudlanguagetools.constants.UsageScope.User, 
            cloudlanguagetools.constants.UsagePeriod.lifetime,
            cloudlanguagetools.constants.Service.Azure,
            'trial_key_1',
            cloudlanguagetools.constants.ApiKeyType.trial,
            {'character_limit': 10000})
        self.assertEqual(usage_slice_monthly_global.over_quota(9985, 200), False)

        self.assertEqual(usage_slice_monthly_global.over_quota(10005, 200), True)

    def test_quotas_global(self):
        usage_slice_monthly_global = quotas.UsageSlice(
            cloudlanguagetools.constants.RequestType.audio,
            cloudlanguagetools.constants.UsageScope.Global, 
            cloudlanguagetools.constants.UsagePeriod.monthly, 
            cloudlanguagetools.constants.Service.Azure,
            'api_key_1',
            cloudlanguagetools.constants.ApiKeyType.patreon,
            {})
        self.assertEqual(usage_slice_monthly_global.over_quota(200000, 30000), False)

        usage_slice_daily_global = quotas.UsageSlice(
            cloudlanguagetools.constants.RequestType.audio,
            cloudlanguagetools.constants.UsageScope.Global, 
            cloudlanguagetools.constants.UsagePeriod.daily, 
            cloudlanguagetools.constants.Service.Azure,
            'api_key_2',
            cloudlanguagetools.constants.ApiKeyType.patreon,
            {})
        self.assertEqual(usage_slice_monthly_global.over_quota(200000, 30000), False)



    def test_quotas_user(self):
        usage_slice_monthly_user = quotas.UsageSlice(
            cloudlanguagetools.constants.RequestType.audio,
            cloudlanguagetools.constants.UsageScope.User, 
            cloudlanguagetools.constants.UsagePeriod.monthly, 
            cloudlanguagetools.constants.Service.Azure,
            'api_key_1',
            cloudlanguagetools.constants.ApiKeyType.patreon,
            {})
        self.assertEqual(usage_slice_monthly_user.over_quota(300000, 30000), False)

        usage_slice_daily_user = quotas.UsageSlice(
            cloudlanguagetools.constants.RequestType.audio,
            cloudlanguagetools.constants.UsageScope.User, 
            cloudlanguagetools.constants.UsagePeriod.daily, 
            cloudlanguagetools.constants.Service.Azure,
            'api_key_2',
            cloudlanguagetools.constants.ApiKeyType.patreon,
            {})
        self.assertEqual(usage_slice_daily_user.over_quota(50000, 30000), False)
        self.assertEqual(usage_slice_daily_user.over_quota(200000, 30000), False) # no daily limit anymore

    def test_quotas_patreon(self):
        usage_slice_monthly_patreon_user = quotas.UsageSlice(
            cloudlanguagetools.constants.RequestType.audio,
            cloudlanguagetools.constants.UsageScope.User, 
            cloudlanguagetools.constants.UsagePeriod.patreon_monthly, 
            cloudlanguagetools.constants.Service.Azure,
            'api_key_1',
            cloudlanguagetools.constants.ApiKeyType.patreon,
            {})
        self.assertEqual(usage_slice_monthly_patreon_user.over_quota(249999, 2), False)
        self.assertEqual(usage_slice_monthly_patreon_user.over_quota(250001, 2), True)

    def test_quotas_easypronunciation(self):
        # restrict daily usage for a given user
        usage_slice_daily_easypronuncation_user = quotas.UsageSlice(
            cloudlanguagetools.constants.RequestType.transliteration,
            cloudlanguagetools.constants.UsageScope.User, 
            cloudlanguagetools.constants.UsagePeriod.daily, 
            cloudlanguagetools.constants.Service.EasyPronunciation,
            'api_key_1',
            cloudlanguagetools.constants.ApiKeyType.getcheddar,
            {})
        self.assertEqual(usage_slice_daily_easypronuncation_user.over_quota(136000, 2000), False)
        self.assertEqual(usage_slice_daily_easypronuncation_user.over_quota(136001, 2000), True)
        self.assertEqual(usage_slice_daily_easypronuncation_user.over_quota(17000, 2001), False)

        usage_slice_monthly_easypronuncation_user = quotas.UsageSlice(
            cloudlanguagetools.constants.RequestType.transliteration,
            cloudlanguagetools.constants.UsageScope.User, 
            cloudlanguagetools.constants.UsagePeriod.monthly, 
            cloudlanguagetools.constants.Service.EasyPronunciation,
            'api_key_1',
            cloudlanguagetools.constants.ApiKeyType.getcheddar,
            {})        
        self.assertEqual(usage_slice_monthly_easypronuncation_user.over_quota(17001, 2000), False)
        self.assertEqual(usage_slice_monthly_easypronuncation_user.over_quota(17000, 2001), False)            

    def test_quotas_forvo(self):
        # restrict daily usage for a given user
        usage_slice_daily_forvo_user = quotas.UsageSlice(
            cloudlanguagetools.constants.RequestType.audio,
            cloudlanguagetools.constants.UsageScope.User, 
            cloudlanguagetools.constants.UsagePeriod.daily, 
            cloudlanguagetools.constants.Service.Forvo,
            'api_key_1',
            cloudlanguagetools.constants.ApiKeyType.getcheddar,
            {})
        self.assertEqual(usage_slice_daily_forvo_user.over_quota(24585, 7000), False)
        self.assertEqual(usage_slice_daily_forvo_user.over_quota(24585, 7001), True)
        self.assertEqual(usage_slice_daily_forvo_user.over_quota(100000, 7000), False)        

    def test_build_key_suffix(self):
        # clt:usage:user:daily:20210209:Naver:audio:zrrVDK3svzDOLzI6

        usage_slice_daily_user = quotas.UsageSlice(
            cloudlanguagetools.constants.RequestType.audio,
            cloudlanguagetools.constants.UsageScope.User, 
            cloudlanguagetools.constants.UsagePeriod.daily, 
            cloudlanguagetools.constants.Service.Naver,
            'zrrVDK3svzDOLzI6',
            cloudlanguagetools.constants.ApiKeyType.patreon,
            {})
        
        date_str = datetime.datetime.today().strftime('%Y%m%d')
        self.assertEqual(usage_slice_daily_user.build_key_suffix(), f'user:daily:{date_str}:Naver:audio:zrrVDK3svzDOLzI6')


        # clt:usage:user:patreon_monthly:202102:zrrVDK3svzDOLzI6
        usage_slice_monthly_user = quotas.UsageSlice(
            cloudlanguagetools.constants.RequestType.audio,
            cloudlanguagetools.constants.UsageScope.User, 
            cloudlanguagetools.constants.UsagePeriod.patreon_monthly, 
            cloudlanguagetools.constants.Service.Azure,
            'zrrVDK3svzDOLzI6',
            cloudlanguagetools.constants.ApiKeyType.patreon,
            {})
        date_str = datetime.datetime.today().strftime('%Y%m')
        self.assertEqual(usage_slice_monthly_user.build_key_suffix(), f'user:patreon_monthly:{date_str}:zrrVDK3svzDOLzI6')

        # clt:usage:user:monthly:202102:Azure:audio:zrrVDK3svzDOLzI6
        usage_slice_monthly_user = quotas.UsageSlice(
            cloudlanguagetools.constants.RequestType.audio,
            cloudlanguagetools.constants.UsageScope.User, 
            cloudlanguagetools.constants.UsagePeriod.monthly, 
            cloudlanguagetools.constants.Service.Azure,
            'zrrVDK3svzDOLzI6',
            cloudlanguagetools.constants.ApiKeyType.patreon,
            {})
        
        date_str = datetime.datetime.today().strftime('%Y%m')
        self.assertEqual(usage_slice_monthly_user.build_key_suffix(), f'user:monthly:{date_str}:Azure:audio:zrrVDK3svzDOLzI6')

        # clt:usage:global:monthly:202102:Amazon:audio
        usage_slice_monthly_global = quotas.UsageSlice(
            cloudlanguagetools.constants.RequestType.audio,
            cloudlanguagetools.constants.UsageScope.Global, 
            cloudlanguagetools.constants.UsagePeriod.monthly, 
            cloudlanguagetools.constants.Service.Amazon,
            'zrrVDK3svzDOLzI6',
            cloudlanguagetools.constants.ApiKeyType.patreon,
            {})
        
        date_str = datetime.datetime.today().strftime('%Y%m')
        self.assertEqual(usage_slice_monthly_global.build_key_suffix(), f'global:monthly:{date_str}:Amazon:audio')

        # clt:usage:global:daily:20210205:MandarinCantonese:transliteration
        usage_slice_monthly_user = quotas.UsageSlice(
            cloudlanguagetools.constants.RequestType.transliteration,
            cloudlanguagetools.constants.UsageScope.Global, 
            cloudlanguagetools.constants.UsagePeriod.daily, 
            cloudlanguagetools.constants.Service.MandarinCantonese,
            'zrrVDK3svzDOLzI6',
            cloudlanguagetools.constants.ApiKeyType.patreon,
            {})
        
        date_str = datetime.datetime.today().strftime('%Y%m%d')
        self.assertEqual(usage_slice_monthly_user.build_key_suffix(), f'global:daily:{date_str}:MandarinCantonese:transliteration')

        # clt:usage:user:lifetime:zrrVDK3svzDOLzI6
        usage_slice_lifetime_user = quotas.UsageSlice(
            cloudlanguagetools.constants.RequestType.audio,
            cloudlanguagetools.constants.UsageScope.User, 
            cloudlanguagetools.constants.UsagePeriod.lifetime, 
            cloudlanguagetools.constants.Service.Azure,
            'zrrVDK3svzDOLzI6',
            cloudlanguagetools.constants.ApiKeyType.patreon,
            {})

        self.assertEqual(usage_slice_lifetime_user.build_key_suffix(), f'user:lifetime:zrrVDK3svzDOLzI6')

        # clt:usage:user:recurring:zrrVDK3svzDOLzI6
        usage_slice_recurring_user = quotas.UsageSlice(
            None,
            cloudlanguagetools.constants.UsageScope.User, 
            cloudlanguagetools.constants.UsagePeriod.recurring, 
            None,
            'zrrVDK3svzDOLzI6',
            cloudlanguagetools.constants.ApiKeyType.getcheddar,
            {})

        self.assertEqual(usage_slice_recurring_user.build_key_suffix(), f'user:recurring:zrrVDK3svzDOLzI6')        