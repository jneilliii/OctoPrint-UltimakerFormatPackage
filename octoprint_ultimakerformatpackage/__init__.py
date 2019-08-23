# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.filemanager.util
import os
from zipfile import ZipFile
from octoprint.util import version
from octoprint.filemanager.analysis import QueueEntry

class UltimakerFormatPackagePlugin(octoprint.plugin.SettingsPlugin,
								   octoprint.plugin.AssetPlugin,
								   octoprint.plugin.TemplatePlugin,
								   octoprint.plugin.EventHandlerPlugin):

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			installed=True
		)

	##~~ AssetPlugin mixin

	def get_assets(self):
		return dict(
			js=["js/UltimakerFormatPackage.js"],
			css=["css/UltimakerFormatPackage.css"]
		)

	##~~ EventHandlerPlugin mixin

	def on_event(self, event, payload):
		if event == "FileAdded" and "ufp" in payload["type"]:
			# Add ufp file to analysisqueue
			old_name = self._settings.global_get_basefolder("uploads") + "/" + payload["path"]
			new_name = old_name + ".gcode"
			os.rename(old_name, new_name)
			printer_profile = self._printer_profile_manager.get("_default")
			if version.get_octoprint_version() > version.get_comparable_version("1.3.9"):
				entry = QueueEntry(payload["name"] + ".gcode",payload["path"] + ".gcode","gcode",payload["storage"],new_name, printer_profile, None)
			else:
				entry = QueueEntry(payload["name"] + ".gcode",payload["path"] + ".gcode","gcode",payload["storage"],new_name, printer_profile)
			self._analysis_queue.enqueue(entry,high_priority=True)
		if event == "FileRemoved" and payload["name"].endswith(".ufp.gcode"):
			thumbnail = "%s/%s" % (self.get_plugin_data_folder(), payload["name"].replace(".ufp.gcode", ".png"))
			ufp_file = "%s/%s" % (self.get_plugin_data_folder(), payload["name"].replace(".ufp.gcode", ".ufp"))
			if os.path.exists(thumbnail):
				os.remove(thumbnail)
			if os.path.exists(ufp_file):
				os.remove(ufp_file)

	##-- UFP upload extenstion tree hook
	def get_extension_tree(self, *args, **kwargs):
		return dict(
			machinecode=dict(
				ufp=["ufp"]
			)
		)

	##~~ UFP upload preprocessor hook
	def ufp_upload(self, path, file_object, links=None, printer_profile=None, allow_overwrite=True, *args, **kwargs):
		ufp_extensions = [".ufp"]
		name, extension = os.path.splitext(file_object.filename)
		if extension in ufp_extensions:
			file_object.save(self.get_plugin_data_folder() + "/" + file_object.filename)
			with ZipFile(self.get_plugin_data_folder() + "/" + file_object.filename,'r') as zipObj:
				with open(self.get_plugin_data_folder() + "/" + name + ".png", 'wb') as thumbnail:
					thumbnail.write(zipObj.read("/Metadata/thumbnail.png"))
				with open(self.get_plugin_data_folder() + "/" + name + ".gcode", 'wb') as f:
					f.write(zipObj.read("/3D/model.gcode"))
				return octoprint.filemanager.util.DiskFileWrapper(name + ".gcode", self.get_plugin_data_folder() + "/" + name + ".gcode")
		return file_object

	##~~ Routes hook
	def route_hook(self, server_routes, *args, **kwargs):
		from octoprint.server.util.tornado import LargeResponseHandler, UrlProxyHandler, path_validation_factory
		from octoprint.util import is_hidden_path
		return [
				(r"/(.*)", LargeResponseHandler, dict(path=self.get_plugin_data_folder(),
																as_attachment=False,
																path_validation=path_validation_factory(lambda path: not is_hidden_path(path),status_code=404)))
				]

	##~~ Softwareupdate hook

	def get_update_information(self):
		return dict(
			UltimakerFormatPackage=dict(
				displayName="Ultimaker Format Package",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="jneilliii",
				repo="OctoPrint-UltimakerFormatPackage",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/jneilliii/OctoPrint-UltimakerFormatPackage/archive/{target_version}.zip"
			)
		)

__plugin_name__ = "Ultimaker Format Package"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = UltimakerFormatPackagePlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.filemanager.extension_tree": __plugin_implementation__.get_extension_tree,
		"octoprint.filemanager.preprocessor": __plugin_implementation__.ufp_upload,
		"octoprint.server.http.routes": __plugin_implementation__.route_hook
	}

