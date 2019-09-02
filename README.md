# StatBot
StatBot is designed to report monthly discord server statistics about users, channels and more!

## Usage
### Installation
To run this bot yourself you will need to first [create a discord bot](https://discordapp.com/developers/applications/) by creating an application and then making a bot account, and then create a file called `dctoken.py` that contains the following:
```
token = "my-discord-bot-token-goes-here"
```
Make sure to copy the bot token and not the application token. Then, to add the bot to your server, visit:
```
https://discordapp.com/oauth2/authorize?client_id=MY-DISCORD-APPLICATION-ID&scope=bot&permissions=1543629888
```
Make sure to replace the `client_id` field with the application's client id.
### General
All commands take the form `!command [months ago]` and will return data for a one month period of time. By default they return data for the current month and take an optional argument to specify the month to process. For example, `!count 1` will return data for the previous month and likewise `!count 2` will return data for two months ago. All months use the timezone UTC-4.
### `!users [months_ago]`
This command collects and displays a sorted list of the number of messages each user has sent in the given month.

### `!channels [months_ago]`
This command collects and displays a sorted list of the number of messages sent in each channel in the given month.

### `!times [months_ago]`
This command displays a chart of the total number of messages sent in the given month broken up into 30 minute intervals throughout the day. One `#` in the chart represents 10 messages.

### `!count [months_ago]`
This convenience command simply combines the output of `!users` and `!channels` without needing to poll discord for the message history twice.
