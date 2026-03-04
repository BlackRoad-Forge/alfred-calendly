#!/usr/bin/python
# encoding: utf-8

import sys

from workflow import Workflow3, PasswordNotFound, ICON_ACCOUNT, ICON_EJECT
from workflow.background import run_in_background
import constants as c
from migration import process_migration

log = None

'''
Concatenates Name and Scheduling URL of a event type to a searchable token.
'''
def get_search_key_for_event_types(event_type):
    elements = [
        event_type['name'],
        event_type['scheduling_url']
    ]
    return u' '.join(elements)


'''
Starts a thread that asynchronously checks for updated event types from Calendly once the cache is older than 300 s
'''
def preload_event_types_regularly():
    if not wf.cached_data_fresh(c.CACHE_EVENT_TYPES, max_age=300):
        log.debug("Event Types Cache expired.")
        cmd = ['/usr/bin/python', wf.workflowfile('cy_preload_event_types.py')]
        run_in_background('preload_event_types', cmd)
    else:
        log.debug("Event Types in Cache still fresh.")


def main(wf):
    # type: (Workflow3) -> None

    log.debug("Current Version: %s", wf.version)

    # Show notification when new workflow version exists
    if wf.update_available:
        wf.add_item(
            title="New Workflow Version Available!",
            subtitle="Activate this action in order to run the update.",
            valid="False",
            autocomplete="workflow:update"
        )

    # Process user input from Alfred
    user_input = wf.args[0]
    command = query = ""
    if len(user_input) > 0:
        log.debug("Input: %s" % user_input)
        command = user_input.split()[0]
        query = user_input[len(command) + 1:]

    # Check whether the workflow has an access token of Calendly set
    try:
        access_token = wf.get_password(c.ACCESS_TOKEN)
    except PasswordNotFound:
        access_token = None

    '''+++++++++++++++++++++++++++++++++++++++++++++++++
        Configuration Phase
    +++++++++++++++++++++++++++++++++++++++++++++++++'''
    if access_token is None:
        if command == "":
            wf.add_item(
                title="Personal Access Token required.",
                subtitle="Hit ENTER to proceed.",
                autocomplete="%s " % c.CMD_SET_ACCESS_TOKEN,
                valid=False,
                icon=ICON_ACCOUNT
            )
        elif command == c.CMD_SET_ACCESS_TOKEN:
            if query == '':
                wf.add_item(
                    title="Paste your Personal Access Token here.",
                    subtitle="If you don't have one, simply press ENTER.",
                    arg=c.CMD_OBTAIN_ACCESS_TOKEN,
                    valid=True
                )
            else:
                wf.add_item(
                    title="Hit ENTER to save your Personal Access Token.",
                    subtitle="You can now use the workflow. Happy scheduling!",
                    arg="%s %s" % (c.CMD_SET_ACCESS_TOKEN, query),
                    valid=True
                )
        wf.send_feedback()
        return 0

    '''+++++++++++++++++++++++++++++++++++++++++++++++++
        Production Phase
    +++++++++++++++++++++++++++++++++++++++++++++++++'''
    preload_event_types_regularly()

    # Check Stripe availability
    try:
        wf.get_password(c.STRIPE_API_KEY)
        stripe_configured = True
    except PasswordNotFound:
        stripe_configured = False

    '''
    Single Use Link Menu
    '''
    if command == c.CMD_SINGLE_USE_LINK:
        # get all event types from cache
        event_types = wf.cached_data(c.CACHE_EVENT_TYPES, None, max_age=0)

        # if search query entered then filter the event types list
        if query != "":
            event_types = wf.filter(
                query, event_types, key=get_search_key_for_event_types, min_score=20)

        # Show the event types
        if event_types is None or len(event_types) == 0:
            wf.add_item(
                title="No Event Types found.",
                subtitle="... no events you could miss, though.",
                valid=False
            )
        else:

            sorted_event_types = sorted(event_types, key=lambda event_type: event_type["event_stats"] if "event_stats" in event_type else None, reverse=True)

            for event_type in sorted_event_types:
                item = wf.add_item(
                    title=event_type["name"],
                    subtitle="%s || Hits: %d" % (event_type["scheduling_url"], event_type["event_stats"] if "event_stats" in event_type else 0),
                    valid=True,
                    arg="%s %s" % (c.CMD_SINGLE_USE_LINK, event_type["uri"])
                )
                item.add_modifier(
                    "cmd",
                    subtitle="Open Static Link of this Event Type in Browser.",
                    valid=True,
                    arg="%s %s" % (c.CMD_BROWSE_URL,
                                   event_type["scheduling_url"])
                )
                if stripe_configured:
                    item.add_modifier(
                        "alt",
                        subtitle="Create Paid Link (Stripe + Calendly)",
                        valid=True,
                        arg="%s %s" % (c.CMD_PAID_LINK, event_type["uri"])
                    )
        wf.send_feedback()

    # ++++++++++++++++++++++
    # Paid Link Menu
    # ++++++++++++++++++++++
    elif command == c.CMD_PAID_LINK:
        event_types = wf.cached_data(c.CACHE_EVENT_TYPES, None, max_age=0)

        if query != "":
            event_types = wf.filter(
                query, event_types, key=get_search_key_for_event_types, min_score=20)

        if event_types is None or len(event_types) == 0:
            wf.add_item(
                title="No Event Types found.",
                subtitle="Configure event types in Calendly first.",
                valid=False
            )
        else:
            for event_type in event_types:
                wf.add_item(
                    title="$ %s" % event_type["name"],
                    subtitle="Create paid scheduling link via Stripe",
                    valid=True,
                    arg="%s %s" % (c.CMD_PAID_LINK, event_type["uri"])
                )
        wf.send_feedback()

    # ++++++++++++++++++++++
    # Stripe Key Setup
    # ++++++++++++++++++++++
    elif command == c.CMD_SET_STRIPE_KEY:
        if query == '':
            wf.add_item(
                title="Paste your Stripe API Key here.",
                subtitle="Use a restricted key with payment_links and products write access.",
                valid=False
            )
        else:
            wf.add_item(
                title="Hit ENTER to save your Stripe API Key.",
                subtitle="Paid scheduling links will be enabled.",
                arg="%s %s" % (c.CMD_SET_STRIPE_KEY, query),
                valid=True
            )
        wf.send_feedback()

    # ++++++++++++++++++++++
    # Pi Endpoint Setup
    # ++++++++++++++++++++++
    elif command == c.CMD_SET_PI_ENDPOINT:
        if query == '':
            wf.add_item(
                title="Enter your Pi's IP address (e.g. 192.168.1.100)",
                subtitle="Optionally add port: 192.168.1.100:8420",
                valid=False
            )
        else:
            wf.add_item(
                title="Hit ENTER to add Pi endpoint: %s" % query,
                subtitle="Webhooks from Calendly and Stripe will route here.",
                arg="%s %s" % (c.CMD_SET_PI_ENDPOINT, query),
                valid=True
            )
        wf.send_feedback()

    # ++++++++++++++++++++++
    # Logout Menu
    # ++++++++++++++++++++++
    elif command == c.CMD_LOGOUT:
        wf.add_item(
            title="Logout from Calendly",
            subtitle="This detaches the workflow from the currently logged in account. ARE YOU SURE?",
            arg="%s" % c.CMD_LOGOUT,
            valid=True,
            icon=ICON_EJECT
        )
        wf.send_feedback()

    # ++++++++++++++++++++++
    # Main Menu
    # ++++++++++++++++++++++
    else:
        wf.add_item(
            title="Create Single-Use-Link",
            subtitle="Copies the Single-Use-Link to the Clipboard.",
            autocomplete="%s " % c.CMD_SINGLE_USE_LINK,
            valid=False
        )
        if stripe_configured:
            wf.add_item(
                title="Create Paid Link (Stripe)",
                subtitle="Create a Calendly link with Stripe payment attached.",
                autocomplete="%s " % c.CMD_PAID_LINK,
                valid=False
            )
        else:
            wf.add_item(
                title="Setup Stripe Integration",
                subtitle="Add your Stripe API key to enable paid scheduling links.",
                autocomplete="%s " % c.CMD_SET_STRIPE_KEY,
                valid=False
            )
        wf.add_item(
            title="Add Pi Endpoint",
            subtitle="Route webhooks to your Raspberry Pi.",
            autocomplete="%s " % c.CMD_SET_PI_ENDPOINT,
            valid=False
        )
        wf.add_item(
            title="Logout from Calendly",
            subtitle="This detaches the workflow from the currently logged in account.",
            autocomplete="%s" % c.CMD_LOGOUT,
            valid=False,
            icon=ICON_EJECT
        )
        wf.send_feedback()


if __name__ == "__main__":
    wf = Workflow3(
        update_settings={
            "github_slug": "sebwarnke/alfred-calendly",
            "prereleases": False
        }
    )
    log = wf.logger
    process_migration(wf)
    sys.exit(wf.run(main))
