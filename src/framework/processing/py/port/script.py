import logging
import json
import io
from typing import Optional, Literal

import pandas as pd

import port.api.props as props
import port.facebook as facebook
from port.api.commands import (CommandSystemDonate, CommandUIRender, CommandSystemExit)

LOG_STREAM = io.StringIO()

logging.basicConfig(
    #stream=LOG_STREAM,
    level=logging.DEBUG,
    format="%(asctime)s --- %(name)s --- %(levelname)s --- %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)

LOGGER = logging.getLogger("script")


def process(session_id):
    LOGGER.info("Starting the donation flow")
    yield donate_logs(f"{session_id}-tracking")

    platforms = [ ("Facebook", extract_facebook, facebook.validate), ]

    # progress in %
    subflows = len(platforms)
    steps = 2
    step_percentage = (100 / subflows) / steps
    progress = 0

    # For each platform
    # 1. Prompt file extraction loop
    # 2. In case of succes render data on screen
    for platform in platforms:
        platform_name, extraction_fun, validation_fun = platform

        table_list = None
        progress += step_percentage

        # Prompt file extraction loop
        while True:
            LOGGER.info("Prompt for file for %s", platform_name)
            yield donate_logs(f"{session_id}-tracking")

            # Render the propmt file page
            promptFile = prompt_file("application/zip, text/plain, application/json", platform_name)
            file_result = yield render_donation_page(platform_name, promptFile, progress)

            if file_result.__type__ == "PayloadString":
                validation = validation_fun(file_result.value)

                # DDP is recognized: Status code zero
                if validation.status_code.id == 0: 
                    LOGGER.info("Payload for %s", platform_name)
                    yield donate_logs(f"{session_id}-tracking")

                    table_list = extraction_fun(file_result.value, validation)
                    break

                # DDP is not recognized: Different status code
                if validation.status_code.id != 0: 
                    LOGGER.info("Not a valid %s zip; No payload; prompt retry_confirmation", platform_name)
                    yield donate_logs(f"{session_id}-tracking")
                    retry_result = yield render_donation_page(platform_name, retry_confirmation(platform_name), progress)

                    if retry_result.__type__ == "PayloadTrue":
                        continue
                    else:
                        LOGGER.info("Skipped during retry %s", platform_name)
                        yield donate_logs(f"{session_id}-tracking")
                        break
            else:
                LOGGER.info("Skipped %s", platform_name)
                yield donate_logs(f"{session_id}-tracking")
                break

        progress += step_percentage

        # Render data on screen
        if table_list is not None:
            LOGGER.info("Prompt consent; %s", platform_name)
            yield donate_logs(f"{session_id}-tracking")

            # Check if extract something got extracted
            if len(table_list) == 0:
                table_list.append(create_empty_table(platform_name))

            prompt = assemble_tables_into_form(table_list)
            consent_result = yield render_donation_page(platform_name, prompt, progress)

            if consent_result.__type__ == "PayloadJSON":
                LOGGER.info("Data donated; %s", platform_name)
                yield donate_logs(f"{session_id}-tracking")
                yield donate(platform_name, consent_result.value)
            else:
                LOGGER.info("Skipped ater reviewing consent: %s", platform_name)
                yield donate_logs(f"{session_id}-tracking")

    yield exit(0, "Success")
    yield render_end_page()



##################################################################

def assemble_tables_into_form(table_list: list[props.PropsUIPromptConsentFormTable]) -> props.PropsUIPromptConsentForm:
    """
    Assembles all donated data in consent form to be displayed
    """
    return props.PropsUIPromptConsentForm(table_list, [])


def donate_logs(key):
    log_string = LOG_STREAM.getvalue()  # read the log stream
    if log_string:
        log_data = log_string.split("\n")
    else:
        log_data = ["no logs"]

    return donate(key, json.dumps(log_data))


def create_empty_table(platform_name: str) -> props.PropsUIPromptConsentFormTable:
    """
    Show something in case no data was extracted
    """
    title = props.Translatable({
       "en": "Er ging niks mis, maar we konden niks vinden",
       "nl": "Er ging niks mis, maar we konden niks vinden"
    })
    df = pd.DataFrame(["No data found"], columns=["No data found"])
    table = props.PropsUIPromptConsentFormTable(f"{platform_name}_no_data_found", title, df)
    return table



##################################################################
# Extraction functions

def extract_facebook(facebook_zip: str, _) -> list[props.PropsUIPromptConsentFormTable]:
    tables_to_render = []

    df = facebook.group_interactions_to_df(facebook_zip)
    if not df.empty:
        table_title = props.Translatable({"en": "Facebook group interactions", "nl": "Facebook group interactions"})
        table =  props.PropsUIPromptConsentFormTable("facebook_group_interactions", table_title, df)
        tables_to_render.append(table)

    df = facebook.comments_to_df(facebook_zip)
    if not df.empty:
        table_title = props.Translatable({"en": "Facebook comments", "nl": "Facebook comments"})
        table =  props.PropsUIPromptConsentFormTable("facebook_comments", table_title, df)
        tables_to_render.append(table)

    df = facebook.likes_and_reactions_to_df(facebook_zip)
    if not df.empty:
        table_title = props.Translatable({"en": "Facebook likes and reactions", "nl": "Facebook likes and reactions"})
        table =  props.PropsUIPromptConsentFormTable("facebook_likes_and_reactions", table_title, df)
        tables_to_render.append(table)

    df = facebook.your_badges_to_df(facebook_zip)
    if not df.empty:
        table_title = props.Translatable({"en": "Facebook your badges", "nl": "Facebook your badges"})
        table =  props.PropsUIPromptConsentFormTable("facebook_your_badges", table_title, df) 
        tables_to_render.append(table)

    df = facebook.your_posts_to_df(facebook_zip)
    if not df.empty:
        table_title = props.Translatable({"en": "Facebook your posts", "nl": "Facebook your posts"})
        table =  props.PropsUIPromptConsentFormTable("facebook_your_posts", table_title, df) 
        tables_to_render.append(table)

    df = facebook.your_search_history_to_df(facebook_zip)
    if not df.empty:
        table_title = props.Translatable({"en": "Facebook your searh history", "nl": "Facebook your search history"})
        table =  props.PropsUIPromptConsentFormTable("facebook_your_search_history", table_title, df)
        tables_to_render.append(table)

    df = facebook.recently_viewed_to_df(facebook_zip)
    if not df.empty:
        table_title = props.Translatable({"en": "Facebook recently viewed", "nl": "Facebook recently viewed"})
        table =  props.PropsUIPromptConsentFormTable("facebook_recently_viewed", table_title, df) 
        tables_to_render.append(table)

    df = facebook.recently_visited_to_df(facebook_zip)
    if not df.empty:
        table_title = props.Translatable({"en": "Facebook recently visited", "nl": "Facebook recently visited"})
        table =  props.PropsUIPromptConsentFormTable("facebook_recently_visited", table_title, df) 
        tables_to_render.append(table)

    df = facebook.feed_to_df(facebook_zip)
    if not df.empty:
        table_title = props.Translatable({"en": "Facebook feed", "nl": "Facebook feed"})
        table =  props.PropsUIPromptConsentFormTable("facebook_feed", table_title, df) 
        tables_to_render.append(table)

    df = facebook.controls_to_df(facebook_zip)
    if not df.empty:
        table_title = props.Translatable({"en": "Facebook controls", "nl": "Facebook controls"})
        table =  props.PropsUIPromptConsentFormTable("facebook_controls", table_title, df) 
        tables_to_render.append(table)

    df = facebook.group_posts_and_comments_to_df(facebook_zip)
    if not df.empty:
        table_title = props.Translatable({"en": "Facebook group posts and comments", "nl": "Facebook group posts and comments"})
        table =  props.PropsUIPromptConsentFormTable("facebook_group_posts_and_comments", table_title, df) 
        tables_to_render.append(table)
        
    df = facebook.your_posts_check_ins_photos_and_videos_1_to_df(facebook_zip)
    if not df.empty:
        table_title = props.Translatable({"en": "Facebook your posts check ins photos and videos", "nl": "Facebook group posts and comments"})
        table =  props.PropsUIPromptConsentFormTable("facebook_your_posts_check_ins_photos_and_videos", table_title, df) 
        tables_to_render.append(table)

    return tables_to_render



##########################################
# Functions provided by Eyra did not change

def render_end_page():
    page = props.PropsUIPageEnd()
    return CommandUIRender(page)


def render_donation_page(platform, body, progress):
    header = props.PropsUIHeader(props.Translatable({"en": platform, "nl": platform}))

    footer = props.PropsUIFooter(progress)
    page = props.PropsUIPageDonation(platform, header, body, footer)
    return CommandUIRender(page)


def retry_confirmation(platform):
    text = props.Translatable(
        {
            "en": f"Unfortunately, we could not process your {platform} file. If you are sure that you selected the correct file, press Continue. To select a different file, press Try again.",
            "nl": f"Helaas, kunnen we uw {platform} bestand niet verwerken. Weet u zeker dat u het juiste bestand heeft gekozen? Ga dan verder. Probeer opnieuw als u een ander bestand wilt kiezen."
        }
    )
    ok = props.Translatable({"en": "Try again", "nl": "Probeer opnieuw"})
    cancel = props.Translatable({"en": "Continue", "nl": "Verder"})
    return props.PropsUIPromptConfirm(text, ok, cancel)


def prompt_file(extensions, platform):
    description = props.Translatable(
        {
            "en": f"Please follow the download instructions and choose the file that you stored on your device. Click “Skip” at the right bottom, if you do not have a file from {platform}.",
            "nl": f"Volg de download instructies en kies het bestand dat u opgeslagen heeft op uw apparaat. Als u geen {platform} bestand heeft klik dan op “Overslaan” rechts onder."
        }
    )
    return props.PropsUIPromptFileInput(description, extensions)


def donate(key, json_string):
    return CommandSystemDonate(key, json_string)

def exit(code, info):
    return CommandSystemExit(code, info)
