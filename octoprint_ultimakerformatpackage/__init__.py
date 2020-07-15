# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.filemanager.util
import os
from zipfile import ZipFile
from octoprint.util import version, RepeatedTimer
import datetime

class UltimakerFormatPackagePlugin(octoprint.plugin.SettingsPlugin,
								   octoprint.plugin.AssetPlugin,
								   octoprint.plugin.TemplatePlugin,
								   octoprint.plugin.EventHandlerPlugin,
								  octoprint.plugin.SimpleApiPlugin):

	def __init__(self):
		self._fileRemovalTimer = None
		self._fileRemovalLastDeleted = None
		self._fileRemovalLastAdded = None
		self._waitForAnalysis = False
		self._analysis_active = False

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			installed=True,
			installed_version=self._plugin_version,
			inline_thumbnail=False,
			scale_inline_thumbnail=False,
			inline_thumbnail_scale_value="50",
			align_inline_thumbnail=False,
			inline_thumbnail_align_value="left",
			state_panel_thumbnail=True
		)

	##~~ AssetPlugin mixin

	def get_assets(self):
		return dict(
			js=["js/UltimakerFormatPackage.js"],
			css=["css/UltimakerFormatPackage.css"]
		)

	##~~ TemplatePlugin mixin

	def get_template_configs(self):
		return [
			dict(type="settings", custom_bindings=False, template="UltimakerFormatPackage_settings.jinja2"),
		]

	##~~ EventHandlerPlugin mixin

	def on_event(self, event, payload):
		if not event in ["FileAdded","FileRemoved","MetadataAnalysisStarted","MetadataAnalysisFinished","FolderRemoved"]:
			return

		if event == "FolderRemoved" and payload["storage"] == "local":
			import shutil
			shutil.rmtree(self.get_plugin_data_folder() + "/" + payload["path"], ignore_errors=True)
		# Hack that deletes uploaded ufp file from upload path
		if event == "FileAdded" and "ufp" in payload["type"]:
			old_name = payload["path"] # self._settings.global_get_basefolder("uploads") + "/" + 
			ufp_file = self.get_plugin_data_folder() + "/" + payload["path"]
			if os.path.exists(ufp_file):
				os.remove(ufp_file)
			self._file_manager.remove_file("local", old_name)
			return
		if event == "MetadataAnalysisStarted" and payload["path"].endswith(".gcode"):
			self._analysis_active = True
			return
		if event == "MetadataAnalysisFinished" and payload["path"].endswith(".gcode"):
			self._analysis_active = False
			return
		if event == "FileAdded" and payload["path"].endswith(".gcode"):
			self._logger.debug("File added %s" % payload["name"])
			self._fileRemovalLastAdded = payload
		if event == "FileRemoved" and payload["name"].endswith(".gcode"):
			self._logger.debug("File removed %s" % payload["name"])
			self._fileRemovalLastDeleted = payload
			self._fileRemovalTimer_start()
			return

	##~~ File Removal Timer

	def _fileRemovalTimer_start(self):
		if self._fileRemovalTimer is None:
			self._logger.debug("Starting removal timer.")
			self._fileRemovalTimer = RepeatedTimer(5, self._fileRemovalTimer_task)
			self._fileRemovalTimer.start()

	def _fileRemovalTimer_stop(self):
		self._logger.debug("Cancelling timer and setting everything None.")
		if self._fileRemovalTimer is not None:
			self._fileRemovalTimer.cancel()
			self._fileRemovalTimer = None
		if self._fileRemovalLastAdded is not None:
			self._fileRemovalLastAdded = None
		if self._fileRemovalLastDeleted is not None:
			self._fileRemovalLastDeleted = None

	def _fileRemovalTimer_task(self):
		if self._waitForAnalysis:
			return
		if self._fileRemovalLastDeleted is not None:
			self._logger.debug("File removal timer task, _fileRemovalLastDeleted: %s" % self._fileRemovalLastDeleted["name"])
		if self._fileRemovalLastAdded is not None:
			self._logger.debug("File removal timer task, _fileRemovalLastAdded: %s" % self._fileRemovalLastAdded["name"])
		if self._fileRemovalLastDeleted is not None:
			thumbnail = "%s/%s" % (self.get_plugin_data_folder(), self._fileRemovalLastDeleted["path"].replace(".gcode", ".png"))
			ufp_file = "%s/%s" % (self.get_plugin_data_folder(), self._fileRemovalLastDeleted["path"].replace(".gcode", ".ufp"))
			gcode_file = "%s/%s" % (self.get_plugin_data_folder(), self._fileRemovalLastDeleted["path"])
			if self._fileRemovalLastAdded is not None and self._fileRemovalLastDeleted["name"] == self._fileRemovalLastAdded["name"]:
				# copy thumbnail to new path and update metadata
				thumbnail_new = "%s/%s" % (self.get_plugin_data_folder(), self._fileRemovalLastAdded["path"].replace(".gcode", ".png"))
				thumbnail_new_path = os.path.dirname(thumbnail_new)
				self._logger.debug(thumbnail)
				self._logger.debug(thumbnail_new)
				self._logger.debug(thumbnail_new_path)
				if not os.path.exists(thumbnail_new_path):
					os.makedirs(thumbnail_new_path)
				if os.path.exists(thumbnail_new):
					os.remove(thumbnail_new)
				os.rename(thumbnail, thumbnail_new)
				if os.path.exists(thumbnail_new):
					self._logger.debug("Updating thumbnail url.")
					thumbnail_url = "plugin/UltimakerFormatPackage/thumbnail/" + self._fileRemovalLastAdded["path"].replace(".gcode", ".png") + "?" + "{:%Y%m%d%H%M%S}".format(datetime.datetime.now())
					self._file_manager.set_additional_metadata("local", payload["path"], "thumbnail", thumbnail_url, overwrite=True)
					self._file_manager.set_additional_metadata("local", payload["path"], "thumbnail_src", self._identifier, overwrite=True)

			# remove files just in case they are left behind.
			if os.path.exists(thumbnail):
				os.remove(thumbnail)
			if os.path.exists(ufp_file):
				os.remove(ufp_file)
			if os.path.exists(gcode_file):
				os.remove(gcode_file)

		self._fileRemovalTimer_stop()

	def _wait_for_analysis(self):
		self._waitForAnalysis = True

		while True:
			if not self._waitForAnalysis:
				return False

			if not self._analysis_active:
				self._waitForAnalysis = False
				return True

			time.sleep(5)

	##~~ Utility Functions

	def deep_get(self, d, keys, default=None):
		"""
		Example:
			d = {'meta': {'status': 'OK', 'status_code': 200}}
			deep_get(d, ['meta', 'status_code'])		  # => 200
			deep_get(d, ['garbage', 'status_code'])	   # => None
			deep_get(d, ['meta', 'garbage'], default='-') # => '-'
		"""
		assert type(keys) is list
		if d is None:
			return default
		if not keys:
			return d
		return self.deep_get(d.get(keys[0]), keys[1:], default)

	##~~ SimpleApiPlugin mixin

	def _process_gcode(self, gcode_file, results=[]):
		self._logger.debug(gcode_file["path"])
		if gcode_file.get("type") == "machinecode":
			self._logger.debug(gcode_file.get("thumbnail"))
			if gcode_file.get("thumbnail_src", False):
				return results
			if gcode_file.get("refs", False) and gcode_file["refs"].get("thumbnail", False):
				results["no_thumbnail_src"].append(gcode_file["path"])
				self._logger.debug("Setting metadata for %s" % gcode_file["path"])
				self._file_manager.set_additional_metadata("local", gcode_file["path"], "thumbnail", gcode_file["refs"].get("thumbnail").replace("/plugin/UltimakerFormatPackage", "plugin/UltimakerFormatPackage"), overwrite=True)
				self._file_manager.remove_additional_metadata("local", gcode_file["path"], "refs")
				self._file_manager.set_additional_metadata("local", gcode_file["path"], "thumbnail_src", self._identifier, overwrite=True)
		elif gcode_file.get("type") == "folder" and not gcode_file.get("children") == None:
			children = gcode_file["children"]
			for key, file in children.items():
				self._process_gcode(children[key], results)
		return results

	def get_api_commands(self):
		return dict(crawl_files=[])

	def on_api_command(self, command, data):
		import flask
		import json
		from octoprint.server import user_permission
		if not user_permission.can():
			return flask.make_response("Insufficient rights", 403)

		if command == "crawl_files":
			self._logger.debug("Crawling Files")
			FileList = self._file_manager.list_files()
			LocalFiles = FileList["local"]
			results = dict(no_thumbnail=[],no_thumbnail_src=[])
			for key, file in LocalFiles.items():
				results = self._process_gcode(LocalFiles[key], results)
			return flask.jsonify(results)

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
			ufp_filename = self.get_plugin_data_folder() + "/" + path
			png_filename = ufp_filename.replace(".ufp",".png")
			gco_filename = ufp_filename.replace(".ufp", ".gcode")
			ufp_filepath = os.path.dirname(ufp_filename)

			if not os.path.exists(ufp_filepath):
				os.makedirs(ufp_filepath)

			file_object.save(ufp_filename)
			with ZipFile(ufp_filename,'r') as zipObj:
				with open(png_filename, 'wb') as thumbnail:
					thumbnail.write(zipObj.read("/Metadata/thumbnail.png"))
				with open(gco_filename, 'wb') as f:
					f.write(zipObj.read("/3D/model.gcode"))

			file_wrapper = octoprint.filemanager.util.DiskFileWrapper(path.replace(".ufp", ".gcode"), gco_filename, move=False)
			uploaded_file = self._file_manager.add_file("local", file_wrapper.filename, file_wrapper, allow_overwrite=True)
			self._logger.debug('Adding thumbnail url to metadata')
			thumbnail_url = "plugin/UltimakerFormatPackage/thumbnail/" + uploaded_file.replace(".gcode", ".png") + "?" + "{:%Y%m%d%H%M%S}".format(datetime.datetime.now())
			self._file_manager.set_additional_metadata("local", uploaded_file, "thumbnail", thumbnail_url, overwrite=True)
			self._file_manager.set_additional_metadata("local", uploaded_file, "thumbnail_src", self._identifier, overwrite=True)

			return octoprint.filemanager.util.DiskFileWrapper(path, ufp_filename)
		return file_object

	##~~ Routes hook
	def route_hook(self, server_routes, *args, **kwargs):
		from octoprint.server.util.tornado import LargeResponseHandler, UrlProxyHandler, path_validation_factory
		from octoprint.util import is_hidden_path
		return [
				(r"thumbnail/(.*)", LargeResponseHandler, dict(path=self.get_plugin_data_folder(),
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
__plugin_pythoncompat__ = ">=2.7,<4"

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

