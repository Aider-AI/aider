# Licensed under the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

<#
.SYNOPSIS

The installer for uv 0.5.9

.DESCRIPTION

This script detects what platform you're on and fetches an appropriate archive from
https://github.com/astral-sh/uv/releases/download/0.5.9
then unpacks the binaries and installs them to the first of the following locations

    $env:XDG_BIN_HOME
    $env:XDG_DATA_HOME/../bin
    $HOME/.local/bin

It will then add that dir to PATH by editing your Environment.Path registry key

.PARAMETER ArtifactDownloadUrl
The URL of the directory where artifacts can be fetched from

.PARAMETER NoModifyPath
Don't add the install directory to PATH

.PARAMETER Help
Print help

#>

param (
    [Parameter(HelpMessage = "The URL of the directory where artifacts can be fetched from")]
    [string]$ArtifactDownloadUrl = 'https://github.com/astral-sh/uv/releases/download/0.5.9',
    [Parameter(HelpMessage = "Don't add the install directory to PATH")]
    [switch]$NoModifyPath,
    [Parameter(HelpMessage = "Print Help")]
    [switch]$Help
)

$app_name = 'uv'
$app_version = '0.5.9'
if ($env:UV_INSTALLER_GHE_BASE_URL) {
  $installer_base_url = $env:UV_INSTALLER_GHE_BASE_URL
} elseif ($env:UV_INSTALLER_GITHUB_BASE_URL) {
  $installer_base_url = $env:UV_INSTALLER_GITHUB_BASE_URL
} else {
  $installer_base_url = "https://github.com"
}
if ($env:INSTALLER_DOWNLOAD_URL) {
  $ArtifactDownloadUrl = $env:INSTALLER_DOWNLOAD_URL
} else {
  $ArtifactDownloadUrl = "$installer_base_url/astral-sh/uv/releases/download/0.5.9"
}

$receipt = @"
{"binaries":["CARGO_DIST_BINS"],"binary_aliases":{},"cdylibs":["CARGO_DIST_DYLIBS"],"cstaticlibs":["CARGO_DIST_STATICLIBS"],"install_layout":"unspecified","install_prefix":"AXO_INSTALL_PREFIX","modify_path":true,"provider":{"source":"cargo-dist","version":"0.25.2-prerelease.3"},"source":{"app_name":"uv","name":"uv","owner":"astral-sh","release_type":"github"},"version":"0.5.9"}
"@
$receipt_home = "${env:LOCALAPPDATA}\uv"

if ($env:UV_DISABLE_UPDATE) {
  $install_updater = $false
} else {
  $install_updater = $true
}

if ($NoModifyPath) {
    Write-Information "-NoModifyPath has been deprecated; please set UV_NO_MODIFY_PATH=1 in the environment"
}

if ($env:UV_NO_MODIFY_PATH) {
    $NoModifyPath = $true
}

$unmanaged_install = $env:UV_UNMANAGED_INSTALL

if ($unmanaged_install) {
  $NoModifyPath = $true
  $install_updater = $false
}

function Install-Binary($install_args) {
  if ($Help) {
    Get-Help $PSCommandPath -Detailed
    Exit
  }

  Initialize-Environment

  # Platform info injected by dist
  $platforms = @{
    "aarch64-pc-windows-msvc" = @{
      "artifact_name" = "uv-x86_64-pc-windows-msvc.zip"
      "bins" = @("uv.exe", "uvx.exe")
      "libs" = @()
      "staticlibs" = @()
      "zip_ext" = ".zip"
      "aliases" = @{
      }
      "aliases_json" = '{}'
    }
    "i686-pc-windows-msvc" = @{
      "artifact_name" = "uv-i686-pc-windows-msvc.zip"
      "bins" = @("uv.exe", "uvx.exe")
      "libs" = @()
      "staticlibs" = @()
      "zip_ext" = ".zip"
      "aliases" = @{
      }
      "aliases_json" = '{}'
    }
    "x86_64-pc-windows-msvc" = @{
      "artifact_name" = "uv-x86_64-pc-windows-msvc.zip"
      "bins" = @("uv.exe", "uvx.exe")
      "libs" = @()
      "staticlibs" = @()
      "zip_ext" = ".zip"
      "aliases" = @{
      }
      "aliases_json" = '{}'
    }
  }

  $fetched = Download "$ArtifactDownloadUrl" $platforms
  # FIXME: add a flag that lets the user not do this step
  try {
    Invoke-Installer -artifacts $fetched -platforms $platforms "$install_args"
  } catch {
    throw @"
We encountered an error trying to perform the installation;
please review the error messages below.

$_
"@
  }
}

function Get-TargetTriple() {
  try {
    # NOTE: this might return X64 on ARM64 Windows, which is OK since emulation is available.
    # It works correctly starting in PowerShell Core 7.3 and Windows PowerShell in Win 11 22H2.
    # Ideally this would just be
    #   [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture
    # but that gets a type from the wrong assembly on Windows PowerShell (i.e. not Core)
    $a = [System.Reflection.Assembly]::LoadWithPartialName("System.Runtime.InteropServices.RuntimeInformation")
    $t = $a.GetType("System.Runtime.InteropServices.RuntimeInformation")
    $p = $t.GetProperty("OSArchitecture")
    # Possible OSArchitecture Values: https://learn.microsoft.com/dotnet/api/system.runtime.interopservices.architecture
    # Rust supported platforms: https://doc.rust-lang.org/stable/rustc/platform-support.html
    switch ($p.GetValue($null).ToString())
    {
      "X86" { return "i686-pc-windows-msvc" }
      "X64" { return "x86_64-pc-windows-msvc" }
      "Arm" { return "thumbv7a-pc-windows-msvc" }
      "Arm64" { return "aarch64-pc-windows-msvc" }
    }
  } catch {
    # The above was added in .NET 4.7.1, so Windows PowerShell in versions of Windows
    # prior to Windows 10 v1709 may not have this API.
    Write-Verbose "Get-TargetTriple: Exception when trying to determine OS architecture."
    Write-Verbose $_
  }

  # This is available in .NET 4.0. We already checked for PS 5, which requires .NET 4.5.
  Write-Verbose("Get-TargetTriple: falling back to Is64BitOperatingSystem.")
  if ([System.Environment]::Is64BitOperatingSystem) {
    return "x86_64-pc-windows-msvc"
  } else {
    return "i686-pc-windows-msvc"
  }
}

function Download($download_url, $platforms) {
  $arch = Get-TargetTriple

  if (-not $platforms.ContainsKey($arch)) {
    $platforms_json = ConvertTo-Json $platforms
    throw "ERROR: could not find binaries for this platform. Last platform tried: $arch platform info: $platforms_json"
  }

  # Lookup what we expect this platform to look like
  $info = $platforms[$arch]
  $zip_ext = $info["zip_ext"]
  $bin_names = $info["bins"]
  $lib_names = $info["libs"]
  $staticlib_names = $info["staticlibs"]
  $artifact_name = $info["artifact_name"]

  # Make a new temp dir to unpack things to
  $tmp = New-Temp-Dir
  $dir_path = "$tmp\$app_name$zip_ext"

  # Download and unpack!
  $url = "$download_url/$artifact_name"
  Write-Information "Downloading $app_name $app_version ($arch)"
  Write-Verbose "  from $url"
  Write-Verbose "  to $dir_path"
  $wc = New-Object Net.Webclient
  $wc.downloadFile($url, $dir_path)

  Write-Verbose "Unpacking to $tmp"

  # Select the tool to unpack the files with.
  #
  # As of windows 10(?), powershell comes with tar preinstalled, but in practice
  # it only seems to support .tar.gz, and not xz/zstd. Still, we should try to
  # forward all tars to it in case the user has a machine that can handle it!
  switch -Wildcard ($zip_ext) {
    ".zip" {
      Expand-Archive -Path $dir_path -DestinationPath "$tmp";
      Break
    }
    ".tar.*" {
      tar xf $dir_path --strip-components 1 -C "$tmp";
      Break
    }
    Default {
      throw "ERROR: unknown archive format $zip_ext"
    }
  }

  # Let the next step know what to copy
  $bin_paths = @()
  foreach ($bin_name in $bin_names) {
    Write-Verbose "  Unpacked $bin_name"
    $bin_paths += "$tmp\$bin_name"
  }
  $lib_paths = @()
  foreach ($lib_name in $lib_names) {
    Write-Verbose "  Unpacked $lib_name"
    $lib_paths += "$tmp\$lib_name"
  }
  $staticlib_paths = @()
  foreach ($lib_name in $staticlib_names) {
    Write-Verbose "  Unpacked $lib_name"
    $staticlib_paths += "$tmp\$lib_name"
  }

  if (($null -ne $info["updater"]) -and $install_updater) {
    $updater_id = $info["updater"]["artifact_name"]
    $updater_url = "$download_url/$updater_id"
    $out_name = "$tmp\uv-update.exe"

    $wc.downloadFile($updater_url, $out_name)
    $bin_paths += $out_name
  }

  return @{
    "bin_paths" = $bin_paths
    "lib_paths" = $lib_paths
    "staticlib_paths" = $staticlib_paths
  }
}

function Invoke-Installer($artifacts, $platforms) {
  # Replaces the placeholder binary entry with the actual list of binaries
  $arch = Get-TargetTriple

  if (-not $platforms.ContainsKey($arch)) {
    $platforms_json = ConvertTo-Json $platforms
    throw "ERROR: could not find binaries for this platform. Last platform tried: $arch platform info: $platforms_json"
  }

  $info = $platforms[$arch]

  # Forces the install to occur at this path, not the default
  $force_install_dir = $null
  $install_layout = "unspecified"
  # Check the newer app-specific variable before falling back
  # to the older generic one
  if (($env:UV_INSTALL_DIR)) {
    $force_install_dir = $env:UV_INSTALL_DIR
    $install_layout = "flat"
  } elseif (($env:CARGO_DIST_FORCE_INSTALL_DIR)) {
    $force_install_dir = $env:CARGO_DIST_FORCE_INSTALL_DIR
    $install_layout = "flat"
  } elseif ($unmanaged_install) {
    $force_install_dir = $unmanaged_install
    $install_layout = "flat"
  }

  # Check if the install layout should be changed from `flat` to `cargo-home`
  # for backwards compatible updates of applications that switched layouts.
  if (($force_install_dir) -and ($install_layout -eq "flat")) {
    # If the install directory is targeting the Cargo home directory, then
    # we assume this application was previously installed that layout
    # Note the installer passes the path with `\\` separators, but here they are
    # `\` so we normalize for comparison. We don't use `Resolve-Path` because they
    # may not exist.
    $cargo_home = if ($env:CARGO_HOME) { $env:CARGO_HOME } else {
        Join-Path $(if ($HOME) { $HOME } else { "." }) ".cargo"
    }
    if ($force_install_dir.Replace('\\', '\') -eq $cargo_home) {
      $install_layout = "cargo-home"
    }
  }

  # The actual path we're going to install to
  $dest_dir = $null
  $dest_dir_lib = $null
  # The install prefix we write to the receipt.
  # For organized install methods like CargoHome, which have
  # subdirectories, this is the root without `/bin`. For other
  # methods, this is the same as `_install_dir`.
  $receipt_dest_dir = $null
  # Before actually consulting the configured install strategy, see
  # if we're overriding it.
  if (($force_install_dir)) {
    switch ($install_layout) {
      "hierarchical" {
        $dest_dir = Join-Path $force_install_dir "bin"
        $dest_dir_lib = Join-Path $force_install_dir "lib"
      }
      "cargo-home" {
        $dest_dir = Join-Path $force_install_dir "bin"
        $dest_dir_lib = $dest_dir
      }
      "flat" {
        $dest_dir = $force_install_dir
        $dest_dir_lib = $dest_dir
      }
      Default {
        throw "Error: unrecognized installation layout: $install_layout"
      }
    }
    $receipt_dest_dir = $force_install_dir
  }
  if (-Not $dest_dir) {
    # Install to $env:XDG_BIN_HOME
    $dest_dir = if (($base_dir = $env:XDG_BIN_HOME)) {
      Join-Path $base_dir ""
    }
    $dest_dir_lib = $dest_dir
    $receipt_dest_dir = $dest_dir
    $install_layout = "flat"
  }
  if (-Not $dest_dir) {
    # Install to $env:XDG_DATA_HOME/../bin
    $dest_dir = if (($base_dir = $env:XDG_DATA_HOME)) {
      Join-Path $base_dir "../bin"
    }
    $dest_dir_lib = $dest_dir
    $receipt_dest_dir = $dest_dir
    $install_layout = "flat"
  }
  if (-Not $dest_dir) {
    # Install to $HOME/.local/bin
    $dest_dir = if (($base_dir = $HOME)) {
      Join-Path $base_dir ".local/bin"
    }
    $dest_dir_lib = $dest_dir
    $receipt_dest_dir = $dest_dir
    $install_layout = "flat"
  }

  # Looks like all of the above assignments failed
  if (-Not $dest_dir) {
    throw "ERROR: could not find a valid path to install to; please check the installation instructions"
  }

  # The replace call here ensures proper escaping is inlined into the receipt
  $receipt = $receipt.Replace('AXO_INSTALL_PREFIX', $receipt_dest_dir.replace("\", "\\"))
  $receipt = $receipt.Replace('"install_layout":"unspecified"', -join('"install_layout":"', $install_layout, '"'))

  $dest_dir = New-Item -Force -ItemType Directory -Path $dest_dir
  $dest_dir_lib = New-Item -Force -ItemType Directory -Path $dest_dir_lib
  Write-Information "Installing to $dest_dir"
  # Just copy the binaries from the temp location to the install dir
  foreach ($bin_path in $artifacts["bin_paths"]) {
    $installed_file = Split-Path -Path "$bin_path" -Leaf
    Copy-Item "$bin_path" -Destination "$dest_dir" -ErrorAction Stop
    Remove-Item "$bin_path" -Recurse -Force -ErrorAction Stop
    Write-Information "  $installed_file"

    if (($dests = $info["aliases"][$installed_file])) {
      $source = Join-Path "$dest_dir" "$installed_file"
      foreach ($dest_name in $dests) {
          $dest = Join-Path $dest_dir $dest_name
          $null = New-Item -ItemType HardLink -Target "$source" -Path "$dest" -Force -ErrorAction Stop
      }
    }
  }
  foreach ($lib_path in $artifacts["lib_paths"]) {
    $installed_file = Split-Path -Path "$lib_path" -Leaf
    Copy-Item "$lib_path" -Destination "$dest_dir_lib" -ErrorAction Stop
    Remove-Item "$lib_path" -Recurse -Force -ErrorAction Stop
    Write-Information "  $installed_file"
  }
  foreach ($lib_path in $artifacts["staticlib_paths"]) {
    $installed_file = Split-Path -Path "$lib_path" -Leaf
    Copy-Item "$lib_path" -Destination "$dest_dir_lib" -ErrorAction Stop
    Remove-Item "$lib_path" -Recurse -Force -ErrorAction Stop
    Write-Information "  $installed_file"
  }

  $formatted_bins = ($info["bins"] | ForEach-Object { '"' + $_ + '"' }) -join ","
  $receipt = $receipt.Replace('"CARGO_DIST_BINS"', $formatted_bins)
  $formatted_libs = ($info["libs"] | ForEach-Object { '"' + $_ + '"' }) -join ","
  $receipt = $receipt.Replace('"CARGO_DIST_DYLIBS"', $formatted_libs)
  $formatted_staticlibs = ($info["staticlibs"] | ForEach-Object { '"' + $_ + '"' }) -join ","
  $receipt = $receipt.Replace('"CARGO_DIST_STATICLIBS"', $formatted_staticlibs)
  # Also replace the aliases with the arch-specific one
  $receipt = $receipt.Replace('"binary_aliases":{}', -join('"binary_aliases":',  $info['aliases_json']))
  if ($NoModifyPath) {
    $receipt = $receipt.Replace('"modify_path":true', '"modify_path":false')
  }

  # Write the install receipt
  if ($install_updater) {
    $null = New-Item -Path $receipt_home -ItemType "directory" -ErrorAction SilentlyContinue
    # Trying to get Powershell 5.1 (not 6+, which is fake and lies) to write utf8 is a crime
    # because "Out-File -Encoding utf8" actually still means utf8BOM, so we need to pull out
    # .NET's APIs which actually do what you tell them (also apparently utf8NoBOM is the
    # default in newer .NETs but I'd rather not rely on that at this point).
    $Utf8NoBomEncoding = New-Object System.Text.UTF8Encoding $False
    [IO.File]::WriteAllLines("$receipt_home/uv-receipt.json", "$receipt", $Utf8NoBomEncoding)
  }

  # Respect the environment, but CLI takes precedence
  if ($null -eq $NoModifyPath) {
    $NoModifyPath = $env:INSTALLER_NO_MODIFY_PATH
  }

  Write-Information ""
  Write-Information "Installing aider-chat..."
  & "$dest_dir\uv.exe" tool install --force --python python3.12 aider-chat@latest

  if (-not $NoModifyPath) {
    Add-Ci-Path $dest_dir
    if (Add-Path $dest_dir) {
        Write-Information ""
        Write-Information "You need to add $dest_dir to your PATH. Either restart your system or run:"
        Write-Information ""
        Write-Information "    set Path=$dest_dir;%Path%   (cmd)"
        Write-Information "    `$env:Path = `"$dest_dir;`$env:Path`"   (powershell)"
    }
  }
}

# Attempt to do CI-specific rituals to get the install-dir on PATH faster
function Add-Ci-Path($OrigPathToAdd) {
  # If GITHUB_PATH is present, then write install_dir to the file it refs.
  # After each GitHub Action, the contents will be added to PATH.
  # So if you put a curl | sh for this script in its own "run" step,
  # the next step will have this dir on PATH.
  #
  # Note that GITHUB_PATH will not resolve any variables, so we in fact
  # want to write the install dir and not an expression that evals to it
  if (($gh_path = $env:GITHUB_PATH)) {
    Write-Output "$OrigPathToAdd" | Out-File -FilePath "$gh_path" -Encoding utf8 -Append
  }
}

# Try to add the given path to PATH via the registry
#
# Returns true if the registry was modified, otherwise returns false
# (indicating it was already on PATH)
function Add-Path($OrigPathToAdd) {
  Write-Verbose "Adding $OrigPathToAdd to your PATH"
  $RegistryPath = "HKCU:\Environment"
  $PropertyName = "Path"
  $PathToAdd = $OrigPathToAdd

  $Item = if (Test-Path $RegistryPath) {
    # If the registry key exists, get it
    Get-Item -Path $RegistryPath
  } else {
    # If the registry key doesn't exist, create it
    Write-Verbose  "Creating $RegistryPath"
    New-Item -Path $RegistryPath -Force
  }

  $OldPath = ""
  try {
    # Try to get the old PATH value. If that fails, assume we're making it from scratch.
    # Otherwise assume there's already paths in here and use a ; separator
    $OldPath = $Item | Get-ItemPropertyValue -Name $PropertyName
    $PathToAdd = "$PathToAdd;"
  } catch {
    # We'll be creating the PATH from scratch
    Write-Verbose "No $PropertyName Property exists on $RegistryPath (we'll make one)"
  }

  # Check if the path is already there
  #
  # We don't want to incorrectly match "C:\blah\" to "C:\blah\blah\", so we include the semicolon
  # delimiters when searching, ensuring exact matches. To avoid corner cases we add semicolons to
  # both sides of the input, allowing us to pretend we're always in the middle of a list.
  Write-Verbose "Old $PropertyName Property is $OldPath"
  if (";$OldPath;" -like "*;$OrigPathToAdd;*") {
    # Already on path, nothing to do
    Write-Verbose "install dir already on PATH, all done!"
    return $false
  } else {
    # Actually update PATH
    Write-Verbose "Actually mutating $PropertyName Property"
    $NewPath = $PathToAdd + $OldPath
    # We use -Force here to make the value already existing not be an error
    $Item | New-ItemProperty -Name $PropertyName -Value $NewPath -PropertyType String -Force | Out-Null
    return $true
  }
}

function Initialize-Environment() {
  If (($PSVersionTable.PSVersion.Major) -lt 5) {
    throw @"
Error: PowerShell 5 or later is required to install $app_name.
Upgrade PowerShell:

    https://docs.microsoft.com/en-us/powershell/scripting/setup/installing-windows-powershell

"@
  }

  # show notification to change execution policy:
  $allowedExecutionPolicy = @('Unrestricted', 'RemoteSigned', 'ByPass')
  If ((Get-ExecutionPolicy).ToString() -notin $allowedExecutionPolicy) {
    throw @"
Error: PowerShell requires an execution policy in [$($allowedExecutionPolicy -join ", ")] to run $app_name. For example, to set the execution policy to 'RemoteSigned' please run:

    Set-ExecutionPolicy RemoteSigned -scope CurrentUser

"@
  }

  # GitHub requires TLS 1.2
  If ([System.Enum]::GetNames([System.Net.SecurityProtocolType]) -notcontains 'Tls12') {
    throw @"
Error: Installing $app_name requires at least .NET Framework 4.5
Please download and install it first:

    https://www.microsoft.com/net/download

"@
  }
}

function New-Temp-Dir() {
  [CmdletBinding(SupportsShouldProcess)]
  param()
  $parent = [System.IO.Path]::GetTempPath()
  [string] $name = [System.Guid]::NewGuid()
  New-Item -ItemType Directory -Path (Join-Path $parent $name)
}

# PSScriptAnalyzer doesn't like how we use our params as globals, this calms it
$Null = $ArtifactDownloadUrl, $NoModifyPath, $Help
# Make Write-Information statements be visible
$InformationPreference = "Continue"

# The default interactive handler
try {
  Install-Binary "$Args"
} catch {
  Write-Information $_
  exit 1
}
