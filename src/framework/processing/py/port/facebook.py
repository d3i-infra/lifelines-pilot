"""
DDP facebook module

This module contains functions to handle *.jons files contained within a facebook ddp
"""
from pathlib import Path
from typing import Any
import math
import logging
import zipfile
import re

import pandas as pd

import port.unzipddp as unzipddp
import port.helpers as helpers
from port.validate import (
    DDPCategory,
    StatusCode,
    ValidateInput,
    Language,
    DDPFiletype,
)

logger = logging.getLogger(__name__)

DDP_CATEGORIES = [
    DDPCategory(
        id="json_en",
        ddp_filetype=DDPFiletype.JSON,
        language=Language.EN,
        known_files=[
            "events_interactions.json",
            "group_interactions.json",
            "people_and_friends.json",
            "advertisers_using_your_activity_or_information.json",
            "advertisers_you've_interacted_with.json",
            "apps_and_websites.json",
            "your_off-facebook_activity.json",
            "comments.json",
            "posts_and_comments.json",
            "event_invitations.json",
            "your_event_responses.json",
            "accounts_center.json",
            "marketplace_notifications.json",
            "payment_history.json",
            "controls.json",
            "reduce.json",
            "friend_requests_received.json",
            "friend_requests_sent.json",
            "friends.json",
            "rejected_friend_requests.json",
            "removed_friends.json",
            "who_you_follow.json",
            "your_comments_in_groups.json",
            "your_group_membership_activity.json",
            "your_posts_in_groups.json",
            "primary_location.json",
            "primary_public_location.json",
            "timezone.json",
            "notifications.json",
            "pokes.json",
            "ads_interests.json",
            "friend_peer_group.json",
            "pages_and_profiles_you_follow.json",
            "pages_and_profiles_you've_recommended.json",
            "pages_and_profiles_you've_unfollowed.json",
            "pages_you've_liked.json",
            "polls_you_voted_on.json",
            "your_uncategorized_photos.json",
            "your_videos.json",
            "language_and_locale.json",
            "live_video_subscriptions.json",
            "profile_information.json",
            "profile_update_history.json",
            "your_local_lists.json",
            "your_saved_items.json",
            "your_search_history.json",
            "account_activity.json",
            "authorized_logins.json",
            "browser_cookies.json",
            "email_address_verifications.json",
            "ip_address_activity.json",
            "login_protection_data.json",
            "logins_and_logouts.json",
            "mobile_devices.json",
            "record_details.json",
            "where_you're_logged_in.json",
            "your_facebook_activity_history.json",
            "archived_stories.json",
            "location.json",
            "recently_viewed.json",
            "recently_visited.json",
            "your_topics.json",
        ],
    )
]

STATUS_CODES = [
    StatusCode(id=0, description="Valid DDP", message=""),
    StatusCode(id=1, description="Not a valid DDP", message=""),
    StatusCode(id=2, description="Bad zipfile", message=""),
]


def validate(zfile: Path) -> ValidateInput:
    """
    Validates the input of an Instagram zipfile
    """

    validation = ValidateInput(STATUS_CODES, DDP_CATEGORIES)

    try:
        paths = []
        with zipfile.ZipFile(zfile, "r") as zf:
            for f in zf.namelist():
                p = Path(f)
                if p.suffix in (".html", ".json"):
                    logger.debug("Found: %s in zip", p.name)
                    paths.append(p.name)

        validation.infer_ddp_category(paths)
        if validation.ddp_category.id is None:
            validation.set_status_code(1)
        else:
            validation.set_status_code(0)

    except zipfile.BadZipFile:
        validation.set_status_code(2)

    return validation


def group_interactions_to_df(facebook_zip: str) -> pd.DataFrame:

    b = unzipddp.extract_file_from_zip(facebook_zip, "group_interactions.json")
    d = unzipddp.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["group_interactions_v2"][0]["entries"]
        for item in items:
            datapoints.append((
                item.get("data", {}).get("name", None),
                item.get("data", {}).get("value", '').split(" ")[0],
                item.get("data", {}).get("uri", None)
            ))
        out = pd.DataFrame(datapoints, columns=["Group name", "Times Interacted", "Group Link"])
        out = out.sort_values(by="Times Interacted", ascending=False)

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out



def groups_to_list(facebook_zip: str) -> list:

    b = unzipddp.extract_file_from_zip(facebook_zip, "group_interactions.json")
    d = unzipddp.read_json_from_bytes(b)

    out = []

    try:
        items = d["group_interactions_v2"][0]["entries"]
        for item in items:
            out.append(
                item.get("data", {}).get("name", None)
            )

        out = [item for item in out if isinstance(item, str)]
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out



def comments_to_df(facebook_zip: str) -> pd.DataFrame:

    b = unzipddp.extract_file_from_zip(facebook_zip, "comments.json")
    d = unzipddp.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["comments_v2"]
        for item in items:
            datapoints.append((
                item.get("title", ""),
                item["data"][0].get("comment", {}).get("comment", ""),
                helpers.epoch_to_iso(item.get("timestamp", {}))
            ))
        out = pd.DataFrame(datapoints, columns=["Action", "Comment", "Date"])

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out



def likes_and_reactions_to_df(facebook_zip: str) -> pd.DataFrame:

    b = unzipddp.extract_file_from_zip(facebook_zip, "likes_and_reactions_1.json")
    d = unzipddp.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        for item in d:
            datapoints.append((
                item.get("title", ""),
                item["data"][0].get("reaction", {}).get("reaction", ""),
                helpers.epoch_to_iso(item.get("timestamp", {}))
            ))
        out = pd.DataFrame(datapoints, columns=["Action", "Reaction", "Date"])

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def your_badges_to_df(facebook_zip: str) -> pd.DataFrame:

    b = unzipddp.extract_file_from_zip(facebook_zip, "your_badges.json")
    d = unzipddp.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        for k, v in d["group_badges_v2"].items():
            datapoints.append((
                k,
                ', '.join(v),
                len(v)
            ))
        out = pd.DataFrame(datapoints, columns=["Group name", "Badges", "Number of badges"])
        out = out.sort_values(by="Number of badges", ascending=False)

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def find_items(d: dict[Any, Any],  key_to_match: str) -> str:
    """
    d is a denested dict
    match all keys in d that contain key_to_match

    return the value beloning to that key that are the least nested
    In case of no match return empty string

    example:
    key_to_match = asd

    asd-asd-asd-asd-asd-asd: 1
    asd-asd: 2
    qwe: 3

    returns 2

    This function is needed because your_posts_1.json contains a wide variety of nestedness per post
    """
    out = ""
    pattern = r"{}".format(f"^.*{key_to_match}.*$")
    depth = math.inf

    try:
        for k, v in d.items():
            if re.match(pattern, k):
                depth_current_match = k.count("-")
                if depth_current_match < depth:
                    depth = depth_current_match
                    out = str(v)
    except Exception as e:
        logger.error("bork bork: %s", e)

    return out
            


def your_posts_to_df(facebook_zip: str) -> pd.DataFrame:

    b = unzipddp.extract_file_from_zip(facebook_zip, "your_posts_1.json")
    d = unzipddp.read_json_from_bytes(b)
    if isinstance(d, dict) == True:
        d = [d]

    out = pd.DataFrame()
    datapoints = []

    try:
        for item in d:
            denested_dict = helpers.dict_denester(item)

            datapoints.append((
                find_items(denested_dict, "title"),
                find_items(denested_dict, "post"),
                helpers.epoch_to_iso(find_items(denested_dict, "timestamp")),
                find_items(denested_dict, "url"),
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "Post", "Date", "Url"])
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def your_posts_check_ins_photos_and_videos_1_to_df(facebook_zip: str) -> pd.DataFrame:

    b = unzipddp.extract_file_from_zip(facebook_zip, "your_posts__check_ins__photos_and_videos_1.json")
    d = unzipddp.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        for item in d:
            denested_dict = helpers.dict_denester(item)

            datapoints.append((
                find_items(denested_dict, "title"),
                find_items(denested_dict, "post"),
                helpers.epoch_to_iso(find_items(denested_dict, "timestamp")),
                find_items(denested_dict, "url"),
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "Post", "Date", "Url"])
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def your_search_history_to_df(facebook_zip: str) -> pd.DataFrame:

    b = unzipddp.extract_file_from_zip(facebook_zip, "your_search_history.json")
    d = unzipddp.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["searches_v2"]
        for item in items:
            datapoints.append((
                item["data"][0].get("text", ""),
                helpers.epoch_to_iso(item.get("timestamp", {}))
            ))

        out = pd.DataFrame(datapoints, columns=["Search Term", "Date"])
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def recently_viewed_to_df(facebook_zip: str) -> pd.DataFrame:
    b = unzipddp.extract_file_from_zip(facebook_zip, "recently_viewed.json")
    d = unzipddp.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["recently_viewed"]
        for item in items:

            if "entries" in item:
                for entry in item["entries"]:
                    datapoints.append((
                        item.get("name", ""),
                        entry.get("data", {}).get("name", ""),
                        entry.get("data", {}).get("uri", ""),
                        helpers.epoch_to_iso(entry.get("timestamp"))
                    ))

            # The nesting goes deeper
            if "children" in item:
                for child in item["children"]:
                    for entry in child["entries"]:
                        datapoints.append((
                            child.get("name", ""),
                            entry.get("data", {}).get("name", ""),
                            entry.get("data", {}).get("uri", ""),
                            helpers.epoch_to_iso(entry.get("timestamp"))
                        ))

        out = pd.DataFrame(datapoints, columns=["Watched", "Name", "Link", "Date"])
        out = out.sort_values(by="Date", key=helpers.sort_isotimestamp_empty_timestamp_last)

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out



def recently_visited_to_df(facebook_zip: str) -> pd.DataFrame:
    b = unzipddp.extract_file_from_zip(facebook_zip, "recently_visited.json")
    d = unzipddp.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["visited_things_v2"]
        for item in items:
            if "entries" in item:
                for entry in item["entries"]:
                    datapoints.append((
                        item.get("name", ""),
                        entry.get("data", {}).get("name", ""),
                        entry.get("data", {}).get("uri", ""),
                        helpers.epoch_to_iso(entry.get("timestamp"))
                    ))
        out = pd.DataFrame(datapoints, columns=["Watched", "Name", "Link", "Date"])
        out = out.sort_values(by="Date", key=helpers.sort_isotimestamp_empty_timestamp_last)
        
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def feed_to_df(facebook_zip: str) -> pd.DataFrame:
    b = unzipddp.extract_file_from_zip(facebook_zip, "feed.json")
    d = unzipddp.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["people_and_friends_v2"]
        for item in items:
            if "entries" in item:
                for entry in item["entries"]:
                    datapoints.append((
                        item.get("name", ""),
                        entry.get("data", {}).get("name", ""),
                        entry.get("data", {}).get("uri", ""),
                        helpers.epoch_to_iso(entry.get("timestamp"))
                    ))
        out = pd.DataFrame(datapoints, columns=["Category", "Name", "Link", "Date"])
        out = out.sort_values(by="Date", key=helpers.sort_isotimestamp_empty_timestamp_last)
        
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def controls_to_df(facebook_zip: str) -> pd.DataFrame:
    b = unzipddp.extract_file_from_zip(facebook_zip, "controls.json")
    d = unzipddp.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["controls"]
        for item in items:
            if "entries" in item:
                for entry in item["entries"]:
                    datapoints.append((
                        item.get("name", ""),
                        entry.get("data", {}).get("name", ""),
                        entry.get("data", {}).get("uri", ""),
                        helpers.epoch_to_iso(entry.get("timestamp"))
                    ))
        out = pd.DataFrame(datapoints, columns=["Category", "Name", "Link", "Date"])
        out = out.sort_values(by="Date", key=helpers.sort_isotimestamp_empty_timestamp_last)
        
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def group_posts_and_comments_to_df(facebook_zip: str) -> pd.DataFrame:

    b = unzipddp.extract_file_from_zip(facebook_zip, "group_posts_and_comments.json")
    d = unzipddp.read_json_from_bytes(b)

    if not d:
        b = unzipddp.extract_file_from_zip(facebook_zip, "your_posts_in_groups.json")
        d = unzipddp.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        l = d["group_posts_v2"]
        for item in l:
            denested_dict = helpers.dict_denester(item)

            datapoints.append((
                find_items(denested_dict, "title"),
                find_items(denested_dict, "post"),
                find_items(denested_dict, "comment"), # There are no comments in my test data, this is a guess!!
                helpers.epoch_to_iso(find_items(denested_dict, "timestamp")),
                find_items(denested_dict, "url"),
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "Post", "Comment", "Date", "Url"])
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


