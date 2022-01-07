# Whirlpool's Sixth Sense (unofficial)

Unofficial API for Whirlpool's 6th Sense appliances.

As an example on how to use this library, please check the implementation of Home Assistant's [Whirlpool Integration](https://www.home-assistant.io/integrations/whirlpool), or take a look at the `whirlpool_ac.py` file.

If a command does not work, check if it works through the official app.

# NOTICE

Use this at your own risk. If, by using this software, any damage is caused to your appliance, or if you get too hot because your AC got crazy and now you can't sleep, the developers of this software or the manufacturer of your appliance cannot be blamed.


# Using the cli

- listing all Whirpool appliances for an account:

    `python cli.py -l -b "whirlpool" -e "person@mail.com" -p "password123"`

- viewing/controlling a single Maytag appliance:

    `python cli.py -l -b "maytag" -s "SAID123" -e "person@mail.com" -p "password123"`
