# WiiUDownloaderAndroid
An experimental port of the popular WiiUDownloader to Android devices for use with emulators such as Cemu and Wii U consoles.

WiiUDownloader is a Kotlin Android app that allows you to download Wii U games from Nintendo's servers. It has an easy to use GUI to browse and download Wii U titles and save them to a location of your choice. It also supports on device decryption and extraction to be used with popular emulators or on a Wii U console.

To download and decrypt titles, the app uses python and chaquopy with publicly availble code that was modified heavily to work within the app.

## Features

- Browse and search for Wii U games, updates, DLC, demos, and more.
- Download selected titles in a queue of up to 3. Limited to 1 download at a time for performance.
- Decrypt downloaded contents for use on your Wii U console or emulators.
- Filter titles based on name and title ID, as well as title type.
- Select any region (Japan, USA, and Europe) to filter Wii U titles.

## Install

To install WiiUDownloader Android, download the the APK File in releases tab:

- [WiiUDownloader-0.0.1-arm64.apk](https://github.com/loyahdev/WiiUDownloaderAndroid/releases/latest/download/WiiUDownloader-0.0.1-arm64.apk)

## Usage

1. Install the downloaded APK by clicking on it in the Files app,
2. The setup screen will ask for a titlekeys URL and instructions to follow.
3. Once completed you will see a list of titles that can be filtered by region or type (Application, System, DLC, Patch, Demo, All | Europe, USA, Japan).
4. Click on any filter or search by Name and title ID to find a specific title.
5. Click the checkbox button to add selected titles to the download queue with a max of 3 at a time. You can remove them using the X icon in the Queue tab.
6. In the Queue tab click the down arrow icon to move the game to the Downloads page with a max of 1 at a time.
7. When you are directed to the Downloads tab click the "Select Folder" button and choose where you want your title to be stored. (Usually in a Roms directory of choice)
8. Click the "Download" button beside your title and the download progress is shown below until it finishes and automatically decrypts for emulator use.
9. When a title fully completes, you can open the Files app and see the new Title ID folder at the location you selected. Which when set as a directory location in Cemu, it will register as a playable title and you've now successfully used WiiUDownloader!

>[!NOTE]
>All limits on max download are just limitations of Android's Python bridging and as far as I could make possible within the app.

## Important Notes

- WiiUDownloader provides access to Nintendo's servers for downloading titles. Please make sure to follow all legal and ethical guidelines when using this program.
- Downloading and using copyrighted material without proper authorization may violate copyright laws in your country.

---
## Special Thanks! 
I was only able to port this because of [the work from WiiUDownloader by Xpl0itU](https://github.com/Xpl0itU/WiiUDownloader)

Most of the backend code I used was referenced from [ihaveamac's wiiu-things Python code](https://github.com/ihaveamac/wiiu-things) as well as [llakssz's FunKiiU title decryption code](https://github.com/llakssz/FunKiiU)

### License
Apache License 2.0 referred at [LICENSE](https://github.com/loyahdev/WiiUDownloaderAndroid/blob/main/LICENSE)

### Contributing
If you would like to make your own modifications, create a project fork or add a pull request and I'll add it when I have time, thanks!
>[!NOTE]
>This code is very AI assisted as I have never worked with Android before but either way it works for easily downloading Wii U titles.
