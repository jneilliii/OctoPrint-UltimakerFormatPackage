# OctoPrint-UltimakerFormatPackage

This plugin adds support for Ultimaker Format Package (.ufp) files. Ultimaker Format Package files are based on Open Packaging Conventions (OPC) and contain compressed gcode and a preview thumbnail. This format will automatically be used by the [OctoPrint Connection](https://github.com/fieldOfView/Cura-OctoPrintPlugin) plugin in Cura (install via Marketplace) if this plugin is installed.

The preview thumbnail can be shown in OctoPrint from the files list by clicking the newly added image button.

![button](screenshot_button.png)

The thumbnail will open in a modal window.

![thumbnail](screenshot_thumbnail.png)

If enabled in settings the thumbnail can also be embedded as an inline thumbnail within the file list itself. If you use this option it's highly recommended to use Themify to make the file list taller and/or adjust the thumbnail's size.  The image selector for this in Themeify should be `div.row-fluid.inline_thumbnail > img` but I haven't yet tested personally.

![thumbnail](screenshot_inline_thumbnail.png)

## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/jneilliii/OctoPrint-UltimakerFormatPackage/archive/master.zip

## Support My Efforts
I programmed this plugin for fun and do my best effort to support those that have issues with it, please return the favor and support me.

[![paypal](paypal-with-text.png)](https://paypal.me/jneilliii)