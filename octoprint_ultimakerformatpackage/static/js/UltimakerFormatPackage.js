/*
 * View model for OctoPrint-UltimakerFormatPackage
 *
 * Author: jneilliii
 * License: AGPLv3
 */
$(function() {
	function UltimakerformatpackageViewModel(parameters) {
		var self = this;
		self.thumbnail_url = ko.observable('/static/img/tentacle-20x20.png');
		self.thumbnail_title = ko.observable('');

		self.settingsViewModel = parameters[0];
		self.filesViewModel = parameters[1];

		self.filesViewModel.open_thumbnail = function(data) {
			if(data.name.indexOf('.ufp.gcode') > 0){
				var thumbnail_title = data.name.replace('.ufp.gcode','.ufp');
				var thumbnail_url = '/plugin/UltimakerFormatPackage/' + data.name.replace('.ufp.gcode','.png');
				self.thumbnail_url(thumbnail_url);
				self.thumbnail_title(thumbnail_title);
				$('div#thumbnail_viewer').modal("show");
			}
		}

		self.filesViewModel.inline_thumbnail_url = function(data) {
			return '/plugin/UltimakerFormatPackage/' + data.name.replace('.ufp.gcode','.png');
		}

		self.filesViewModel.inline_thumbnail = ko.observable(false);

		self.onBeforeBinding = function() {
			self.filesViewModel.inline_thumbnail(self.settingsViewModel.plugins.UltimakerFormatPackage.inline_thumbnail());
		}

		$(document).ready(function(){
			let regex = /<div class="btn-group action-buttons">([\s\S]*)<.div>/mi;
			let template = '<div class="btn btn-mini" data-bind="click: function() { if ($root.loginState.isUser()) { $root.open_thumbnail($data) } else { return; } }, css: {hidden: name.indexOf(\'.ufp.gcode\') < 0}" title="Show Thumbnail"><i class="fa fa-image"></i></div>';
			let inline_thumbnail_template = '<div class="row-fluid" data-bind="if: ($data.name.indexOf(\'.ufp.gcode\') > -1 && $root.inline_thumbnail() == true)"><img data-bind="attr: {src: $root.inline_thumbnail_url($data)}, visible: ($data.name.indexOf(\'.ufp.gcode\') > -1 && $root.inline_thumbnail() == true), click: function() { if ($root.loginState.isUser()) { $root.open_thumbnail($data) } else { return; } }" width="100%" style="display: none;"/></div>'

			$("#files_template_machinecode").text(function () {
				var return_value = '';
				//if(self.settingsViewModel.plugins.UltimakerFormatPackage.inline_thumbnail() == true){
					return_value = inline_thumbnail_template + $(this).text();
				//} else {
					return_value = return_value.replace(regex, '<div class="btn-group action-buttons">$1	' + template + '></div>');
				//}
				return return_value
			});
		});
	}

	OCTOPRINT_VIEWMODELS.push({
		construct: UltimakerformatpackageViewModel,
		dependencies: ['settingsViewModel', 'filesViewModel'],
		elements: ['div#thumbnail_viewer']
	});
});
