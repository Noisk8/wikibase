<?php

# Optionally load a separate extension configuration file for existing WBS configurations.
# New configuration can be written directly in this file.
if ( is_file( __DIR__ . '/Extensions.php' ) ) {
	require_once __DIR__ . '/Extensions.php';
}

# Add MediaWiki and extension customizations below.
$wgWBRepoSettings['formatterUrlProperty'] = 'P4';

# Identidad visual local de Wikibase WMCO.
$wgLogos = [
    'icon' => "$wgScriptPath/images/wmco-brand.png",
    '1x' => "$wgScriptPath/images/wmco-brand.png",
];

$wgResourceModules['site.wmco.interface.styles'] = [
    'localBasePath' => __DIR__,
    'styles' => [ 'wmco-interface.css' ],
];

$wgHooks['BeforePageDisplay'][] = static function ( $out ) {
    $out->addModuleStyles( 'site.wmco.interface.styles' );
};
