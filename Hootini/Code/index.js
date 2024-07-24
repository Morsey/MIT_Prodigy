/** The simplest use of uibuilder client library
 * See the docs if the client doesn't start on its own.
 */

// Listen for incoming messages from Node-RED and action
// uibuilder.onChange('msg', (msg) => {
//     // do stuff with the incoming msg
// })





/* Riproduce o interrompe audio con ID "id", in base a "source" pieno o vuoto */
function update_audio(source, id) {
    /* Trova elemento dall'ID */
    var audio_obj = document.getElementById(id)

    if (source != "") {
        audio_obj.src = source;   /* Imposta sorgente */
        audio_obj.load();         /* Ricarica */
        audio_obj.play();         /* Riproduce */
        //console.log("Play audio")
    }
    else {
        audio_obj.pause();        /* Pausa */
        audio_obj.currentTime = 0;/* Rimette da capo */
        //console.log("Pause audio")
    }
}


// Listen for incoming messages from Node-RED
uibuilder.onChange('msg', function (msg) {
    /* Audio */
    if (msg.audioSrc != undefined) {
        update_audio(msg.audioSrc, "audioID");
    }
})

