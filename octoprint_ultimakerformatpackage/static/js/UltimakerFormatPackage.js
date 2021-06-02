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
		self.inline_thumbnail = ko.observable();
		self.file_details = ko.observable();
		self.crawling_files = ko.observable(false);
		self.crawl_results = ko.observableArray([]);

		self.settingsViewModel = parameters[0];
		self.filesViewModel = parameters[1];

		self.filesViewModel.UltimakerFormatPackage_open_thumbnail = function(data) {
			if(data.thumbnail_src === "UltimakerFormatPackage"){
				var thumbnail_title = data.path.replace(/\.(?:gco(?:de)?)$/,'');
				var thumbnail_url = ((data.thumbnail) ? data.thumbnail : 'plugin/UltimakerFormatPackage/thumbnail/' + data.path.replace('.ufp.gcode','.png'));
				self.thumbnail_url(thumbnail_url);
				self.thumbnail_title(thumbnail_title);
				self.file_details(data);
				$('div#UltimakerFormatPackage_thumbnail_viewer').modal("show");
			}
		};

		self.DEFAULT_THUMBNAIL_SCALE = "100%";
		self.filesViewModel.UFPthumbnailScaleValue = ko.observable(self.DEFAULT_THUMBNAIL_SCALE);

		self.DEFAULT_THUMBNAIL_ALIGN = "left";
		self.filesViewModel.UFPthumbnailAlignValue = ko.observable(self.DEFAULT_THUMBNAIL_ALIGN);

        self.DEFAULT_THUMBNAIL_POSITION = false;
		self.filesViewModel.UFPthumbnailPositionLeft = ko.observable(self.DEFAULT_THUMBNAIL_POSITION);

		self.crawl_files = function(){
			self.crawling_files(true);
			self.crawl_results([]);
			$.ajax({
				url: API_BASEURL + "plugin/UltimakerFormatPackage",
				type: "POST",
				dataType: "json",
				data: JSON.stringify({
					command: "crawl_files"
				}),
				contentType: "application/json; charset=UTF-8"
			}).done(function(data){
				for (key in data) {
					if(data[key].length){
						self.crawl_results.push({name: ko.observable(key), files: ko.observableArray(data[key])});
					}
				}

				console.log(data);
				if(self.crawl_results().length === 0){
					self.crawl_results.push({name: ko.observable('No convertible files found'), files: ko.observableArray([])});
				}
				self.filesViewModel.requestData({force: true});
				self.crawling_files(false);
			}).fail(function(data){
				self.crawling_files(false);
			});
		};

		self.onBeforeBinding = function() {
			// assign initial scaling
			if (self.settingsViewModel.settings.plugins.UltimakerFormatPackage.scale_inline_thumbnail()==true){
				self.filesViewModel.UFPthumbnailScaleValue(self.settingsViewModel.settings.plugins.UltimakerFormatPackage.inline_thumbnail_scale_value() + "%");
			}

			// assign initial alignment
			if (self.settingsViewModel.settings.plugins.UltimakerFormatPackage.align_inline_thumbnail()==true){
				self.filesViewModel.UFPthumbnailAlignValue(self.settingsViewModel.settings.plugins.UltimakerFormatPackage.inline_thumbnail_align_value());
			}

			// assign initial filelist height
            if(self.settingsViewModel.settings.plugins.UltimakerFormatPackage.resize_filelist()) {
                $('#files > div > div.gcode_files > div.scroll-wrapper').css({'height': self.settingsViewModel.settings.plugins.UltimakerFormatPackage.filelist_height() + 'px'});
            }

            // assign initial position
            if(self.settingsViewModel.settings.plugins.UltimakerFormatPackage.inline_thumbnail_position_left()==true) {
                self.filesViewModel.UFPthumbnailPositionLeft(true);
            }

			// observe scaling changes
			self.settingsViewModel.settings.plugins.UltimakerFormatPackage.scale_inline_thumbnail.subscribe(function(newValue){
				if (newValue == false){
					self.filesViewModel.UFPthumbnailScaleValue(self.DEFAULT_THUMBNAIL_SCALE);
				} else {
					self.filesViewModel.UFPthumbnailScaleValue(self.settingsViewModel.settings.plugins.UltimakerFormatPackage.inline_thumbnail_scale_value() + "%");
				}
			});
			self.settingsViewModel.settings.plugins.UltimakerFormatPackage.inline_thumbnail_scale_value.subscribe(function(newValue){
				self.filesViewModel.UFPthumbnailScaleValue(newValue + "%");
			});
			self.settingsViewModel.settings.plugins.UltimakerFormatPackage.state_panel_thumbnail_scale_value.subscribe(function(newValue){
				$('#UFP_state_thumbnail').attr({'width': self.settingsViewModel.settings.plugins.UltimakerFormatPackage.state_panel_thumbnail_scale_value() + '%'});
			});

			// observe alignment changes
			self.settingsViewModel.settings.plugins.UltimakerFormatPackage.align_inline_thumbnail.subscribe(function(newValue){
				if (newValue == false){
					self.filesViewModel.UFPthumbnailAlignValue(self.DEFAULT_THUMBNAIL_SCALE);
				} else {
					self.filesViewModel.UFPthumbnailAlignValue(self.settingsViewModel.settings.plugins.UltimakerFormatPackage.inline_thumbnail_align_value());
				}
			});
			self.settingsViewModel.settings.plugins.UltimakerFormatPackage.inline_thumbnail_align_value.subscribe(function(newValue){
				self.filesViewModel.UFPthumbnailAlignValue(newValue);
			});

            // observe position changes
            self.settingsViewModel.settings.plugins.UltimakerFormatPackage.inline_thumbnail_position_left.subscribe(function(newValue){
				self.filesViewModel.UFPthumbnailPositionLeft(newValue);
			});

			// observe file list height changes
			self.settingsViewModel.settings.plugins.UltimakerFormatPackage.filelist_height.subscribe(function(newValue){
				if(self.settingsViewModel.settings.plugins.UltimakerFormatPackage.resize_filelist()) {
                    $('#files > div > div.gcode_files > div.scroll-wrapper').css({'height': self.settingsViewModel.settings.plugins.UltimakerFormatPackage.filelist_height() + 'px'});
                }
			});

			self.filesViewModel.listHelper.selectedItem.subscribe(function(data){
				// remove the state panel thumbnail in case it's already there
				if(data){
					console.log(self.settingsViewModel.settings.plugins.UltimakerFormatPackage.state_panel_thumbnail() && (data.thumbnail || data.name.indexOf('.ufp.gcode') > 0) && (data.thumbnail_src === 'UltimakerFormatPackage' || data.name.indexOf('.ufp.gcode') > 0));
					if(self.settingsViewModel.settings.plugins.UltimakerFormatPackage.state_panel_thumbnail() && (data.thumbnail || data.name.indexOf('.ufp.gcode') > 0) && (data.thumbnail_src === 'UltimakerFormatPackage' || data.name.indexOf('.ufp.gcode') > 0)){
						if($('#UFP_state_thumbnail').length){
							$('#UFP_state_thumbnail').attr('src', data.thumbnail);
						} else {
						    $('#state > div > hr:first').after('<img id="UFP_state_thumbnail" class="pull-left" src="'+data.thumbnail+'" width="' + self.settingsViewModel.settings.plugins.UltimakerFormatPackage.state_panel_thumbnail_scale_value() + '%"/>');
						}
					} else {
						$('#UFP_state_thumbnail').remove();
					}
				} else {
					$('#UFP_state_thumbnail').remove();
				}
			});
		};

		$(document).ready(function(){
			let regex = /<div class="btn-group action-buttons">([\s\S]*)<.div>/mi;
			let template = '<div class="btn btn-mini" data-bind="click: function() { if ($root.loginState.isUser()) { $root.UltimakerFormatPackage_open_thumbnail($data) } else { return; } }, visible: $data.thumbnail_src == \'UltimakerFormatPackage\' && $root.settingsViewModel.settings.plugins.UltimakerFormatPackage.inline_thumbnail() == false" title="Show Thumbnail" style="display: none;"><i class="fa fa-image"></i></div>';
			let inline_thumbnail_template = '<div class="inline_thumbnail" ' +
			                                'data-bind="if: $data.thumbnail_src == \'UltimakerFormatPackage\' && $root.settingsViewModel.settings.plugins.UltimakerFormatPackage.inline_thumbnail() == true, style: {\'text-align\': $root.UFPthumbnailAlignValue, \'width\': ($root.UFPthumbnailPositionLeft()) ? $root.UFPthumbnailScaleValue() : \'100%\'}, css: {\'row-fluid\': !$root.UFPthumbnailPositionLeft(), \'pull-left\': $root.UFPthumbnailPositionLeft()}">' +
			                                '<img data-bind="attr: {src: $data.thumbnail, width: $root.UFPthumbnailScaleValue}, ' +
			                                'visible: $data.thumbnail_src == \'UltimakerFormatPackage\' && $root.settingsViewModel.settings.plugins.UltimakerFormatPackage.inline_thumbnail() == true, ' +
			                                'click: function() { if ($root.loginState.isUser()) { $root.UltimakerFormatPackage_open_thumbnail($data) } else { return; } },' +
                                            'style: {\'width\': (!$root.UFPthumbnailPositionLeft()) ? $root.UFPthumbnailScaleValue() : \'100%\' }" ' +
			                                'style="display: none;"/></div>';

			$("#files_template_machinecode").text(function () {
				var return_value = inline_thumbnail_template + $(this).text();
				return_value = return_value.replace(regex, '<div class="btn-group action-buttons">$1	' + template + '></div>');
				return return_value;
			});
		});
	}

	OCTOPRINT_VIEWMODELS.push({
		construct: UltimakerformatpackageViewModel,
		dependencies: ['settingsViewModel', 'filesViewModel'],
		elements: ['div#UltimakerFormatPackage_thumbnail_viewer', '#ufp_crawl_files', '#ufp_crawl_files_results']
	});
});
