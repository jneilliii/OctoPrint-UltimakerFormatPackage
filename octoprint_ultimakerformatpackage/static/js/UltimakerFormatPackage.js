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

		$(document).ready(function(){
			let regex = /<div class="btn-group action-buttons">([\s\S]*)<.div>/mi;
			let template = '<div class="btn btn-mini" data-bind="click: function() { if ($root.loginState.isUser()) { $root.open_thumbnail($data) } else { return; } }, css: {hidden: name.indexOf(\'.ufp.gcode\') < 0}" title="Show Thumbnail"><i class="fa fa-image"></i></div>';

			$("#files_template_machinecode").text(function () {
				return $(this).text().replace(regex, '<div class="btn-group action-buttons">$1	' + template + '></div>');
			});
		});
	}

	OCTOPRINT_VIEWMODELS.push({
		construct: UltimakerformatpackageViewModel,
		dependencies: ['settingsViewModel', 'filesViewModel'],
		elements: ['div#thumbnail_viewer']
	});
});
