import pickle;
import random
import time
from datetime import datetime, timedelta
from time import strptime
from unicodedata import normalize

from requests import ConnectionError
from twitter import error  # Errors generated by Twitter API

from whoknowsbot import twitter_connection
from whoknowsbot.mentions_replies import MentionsReplies


class TwitterBot(object):
    pickle_dict = {}

    def __init__(self):
        self.api = twitter_connection.open_connection()
        self.replies = MentionsReplies(self.api)

    def test(self):
        pass

    def listener(self):
        try:
            f = open('ambiente_de_teste.pckl', 'rb')
            self.pickle_dict = pickle.load(f)
            f.close()

            time_before_processing = datetime.now()

            search_limit = self.get_search_limit()
            new_mentions = self.pickle_dict.get("mentions")

            for mention in new_mentions:
                tweet_text = mention.text
                tweet_text_splitted = tweet_text.split(" ")

                if len(mention.hashtags) > 0:
                    if tweet_text_splitted[1].upper() == "QUANTOSSABEM":
                        self.how_many_knows(mention)
                    elif tweet_text_splitted[1].upper() == "QUEMSABE":
                        self.who_knows(mention)
                    else:
                        pass
                else:
                    pass

            time_after_processing = datetime.now()
            processing_duration = (time_after_processing - time_before_processing).total_seconds()
            {} if processing_duration > 60 else time.sleep(60 - processing_duration)

        # If something happens with the network, sleep for 1 minute and restart bot.
        except ConnectionError as e:
            self.add_error_log(e.args[0].args[0], "Listener")
            time.sleep(60)

    def who_knows(self, mention):
        term = mention.hashtags[0].text
        user_name = mention.user.screen_name
        user_id = mention.user.id
        user_dict = {}

        print("Analisando menção de: " + str(user_name) + " | QUEMSABE")

        followers = self.pickle_dict.get("followers")

        followers_used_term = self.pickle_dict.get("users_who").get(term).get("followers_used_term")

        lowest_timestamp = self.get_lowest_timestamp(followers_used_term)

        if lowest_timestamp == 9999999999999:
            # self.replies.reply_mention_who_know(mention.id, term, mention.user.screen_name, None)
            print("Caí na condição desconhecida do if")
        else:
            current_timestamp = self.get_current_timestamp()
            suitable_follower_score = 0
            suitable_follower_id = None

            for follower in followers_used_term:
                score = 0
                for tweet in followers_used_term[follower]:
                    if tweet.retweeted_status is not None:
                        score = score + 0.5
                    elif tweet.in_reply_to_user_id is not None:
                        score = score + 1.0
                    else:
                        score = score + 0.75

                    tweet_timestamp = self.convert_to_timestamp(tweet.created_at)

                    # TODO: Comentar p/ execução de teste. Valor é volátil por pegar tempo do sistema.
                    # score = score + (1 - (current_timestamp - tweet_timestamp) / (current_timestamp - lowest_timestamp))

                if score > suitable_follower_score:
                    suitable_follower_score = score
                    suitable_follower_id = follower

            suitable_follower_score = ("%.3f" % suitable_follower_score)
            print(str(suitable_follower_id) == self.pickle_dict.get("users_who").get(term).get("suitable_follower_id"))
            print(suitable_follower_score == self.pickle_dict.get("users_who").get(term).get("suitable_follower_score"))
            print("")

            # TODO-Eric descomentar
            # self.replies.reply_mention_who_know(mention.id, term, mention.user.screen_name,
            #                                     suitable_follower_screen_name)

    def how_many_knows(self, mention):
        term = mention.hashtags[0].text
        user_name = mention.user.screen_name
        user_id = mention.user.id
        user_dict = {}
        tweets_dict = {}

        print("Analisando menção de: " + str(user_name) + " | QUANTOSSABEM")

        friends_with_knowledge = 0
        total_of_specialization = 0

        friends = self.pickle_dict.get("friends")

        friends_used_term = self.pickle_dict.get("users_how").get(term).get("friends_used_term")

        for friend in friends_used_term:
            friend_actions_with_term = len(friends_used_term[friend])

            if friend_actions_with_term > 0:
                max_id = 9000000000000000000
                tweets = []

                try:
                    tweets = self.pickle_dict.get("users_how").get(term).get("tweets").get(friend)
                except error.TwitterError as e:
                    self.add_error_log(e.message[1], "GetUserTimeline")

                friends_with_knowledge += 1
                total_of_specialization += friend_actions_with_term / len(tweets)

        proportion_of_knowledge = ("%.3f" % (friends_with_knowledge / len(friends)))
        level_of_specialization = ("%.3f" % (total_of_specialization / len(friends)))

        print(proportion_of_knowledge == self.pickle_dict.get("users_how").get(term).get("proportion_of_knowledge"))
        print(level_of_specialization == self.pickle_dict.get("users_how").get(term).get("level_of_specialization"))
        print("")

        # TODO-Eric descomentar
        # self.replies.reply_mention_how_many(mention.id, term, mention.user.screen_name, friends_with_knowledge,
        #                                     proportion_of_knowledge, level_of_specialization)

    def get_lowest_timestamp(self, users_used_term):
        lowest = 9999999999999

        for user in users_used_term:
            for tweet in users_used_term[user]:
                timestamp = self.convert_to_timestamp(tweet.created_at)

                if timestamp < lowest:
                    lowest = timestamp

        # Return the lesser timestamp among all post analysed
        return lowest

    def get_users_posts_term(self, user_base, term):
        dic_users_used_term = {}

        # Get the date from 7 days ago
        limit_date = datetime.strptime(str(datetime.now()),
                                       '%Y-%m-%d %H:%M:%S.%f') - timedelta(days=7)

        for user in user_base:
            tweets = []
            max_id = 9000000000000000000
            current_time_line = []

            while True:
                time.sleep(1)
                try:
                    current_time_line = self.api.GetUserTimeline(count=200, user_id=user, max_id=max_id,
                                                                 exclude_replies=False, include_rts=True)
                except error.TwitterError as e:
                    self.add_error_log(e.message[1], "GetUserTimeline")

                # For each post collected...
                for tweet in current_time_line:

                    # If term exists into a tweet....
                    if self.accent_remover(tweet.text).count(self.accent_remover(term)) > 0:

                        # Get when the tweet was created in format yyyy-mm-dd HH-MM-SS
                        created = tweet.created_at.split(" ")
                        tweet_date = created[5] + "-" + str(strptime(created[1], '%b').tm_mon) + "-" + created[2] + \
                                     " " + created[3]
                        tweet_date = datetime.strptime(tweet_date, '%Y-%m-%d %H:%M:%S')

                        # If post is recenter than limitDate...
                        if tweet_date > limit_date:
                            tweets.append(tweet)
                        else:
                            break

                # Stop the reading if the user time line finish
                if len(current_time_line) == 0:
                    break
                else:
                    # Get when a post was created in format YYYY-mm-dd HH-MM-SS
                    created = current_time_line[len(current_time_line) - 1].created_at.split(" ")
                    tweet_date = created[5] + "-" + str(strptime(created[1], '%b').tm_mon) + "-" + created[2] + \
                                 " " + created[3]
                    tweet_date = datetime.strptime(tweet_date, '%Y-%m-%d %H:%M:%S')

                    # Define a new limit for search user time line
                    if tweet_date < limit_date:
                        break
                    else:
                        if len(current_time_line) > 0:
                            max_id = current_time_line[len(current_time_line) - 1].id - 1

            dic_users_used_term[user] = tweets

        return dic_users_used_term

    def get_user_base(self, user_id, collect_from):
        # Get user base according type of analysis
        user_base = None
        if collect_from == "friends":
            user_base = self.api.GetFriendIDs(user_id=user_id)
        elif collect_from == "followers":
            user_base = self.api.GetFollowerIDs(user_id=user_id)

        # Get posts no more than 100 people
        if len(user_base) > 100:
            user_base = random.sample(user_base, 100)

        return user_base

    def get_bot_mentions(self, search_limit):
        mentions_collection = []
        max_id = 9000000000000000000
        since_id = int(search_limit)

        while True:
            try:
                # Get the most recent mentions for the authenticating user
                mentions = self.api.GetMentions(since_id=since_id, max_id=max_id, count=200)
            except error.TwitterError as e:
                self.add_error_log(e.message[1], "GetMentions")
                continue

            # Print user and text of mentions collected
            for mention in mentions:
                mentions_collection.append(mention)

            if len(mentions) == 0:
                break
            else:
                max_id = mentions_collection[len(mentions) - 1].id - 1

        # Update value from since_id
        # TODO-Eric Descomentar
        # if len(mentions_collection) > 0:
        #     self.update_search_limit(mentions_collection[0].id)
        #     print(str(len(mentions_collection)) + " menções coletadas. Limite de consulta atualizado")
        # else:
        #     print("Não há novas menções")

        # Return mentions collected
        return mentions_collection

    def get_user_name(self, user_id):
        try:
            user = self.api.GetUser(user_id=user_id)
            return user.screen_name
        except error.TwitterError as e:
            self.add_error_log(e.message[1], "GetUser")

    # TODO-Eric modify algorithm to use this method
    def get_users_timeline(self, users):
        max_id = 9000000000000000000
        user_dict = {}

        for user in users:
            time.sleep(1)

            try:
                current_time_line = self.api.GetUserTimeline(count=200, user_id=user, max_id=max_id,
                                                             exclude_replies=False, include_rts=True)
                user_dict[user] = current_time_line
            except error.TwitterError as e:
                self.add_error_log(e.message[1], "GetUserTimeline")

        return user_dict

    @staticmethod
    def get_search_limit():
        file = open('resources/search_limit.txt', 'r')
        search_limit = file.read()
        file.close()

        return search_limit

    @staticmethod
    def update_search_limit(search_limit):
        file = open('resources/search_limit.txt', 'w')
        file.write(str(search_limit))
        file.close()

    @staticmethod
    def add_error_log(error_message, error_type):
        file = open('resources/errors_log.txt', 'a')
        file.write(str(datetime.now()) + " - " + error_type + ": " + error_message + "\n")
        file.close()

    @staticmethod
    def accent_remover(text):
        return normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII').upper()

    @staticmethod
    def get_current_timestamp():
        # Get current time from the system
        now = datetime.now()

        # Convert DateTime to Timestamp
        now_date_time = str(now.year) + "-" + str(now.month) + "-" + str(now.day) + " " + str(now.hour) + ":" + str(
            now.minute) + ":" + str(now.second)
        now_timestamp = time.mktime(datetime.strptime(now_date_time, "%Y-%m-%d %H:%M:%S").timetuple())

        # Return the current time as timestamp format
        return now_timestamp

    @staticmethod
    def convert_to_timestamp(twitter_date_format):
        created = twitter_date_format.split(" ")
        date_time = created[5] + "-" + str(strptime(created[1], '%b').tm_mon) + "-" + created[2] + " " + created[3]
        # Convert DateTime to Timestamp and return it
        return time.mktime(datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S").timetuple())


who_knows_bot = TwitterBot()
who_knows_bot.listener()
