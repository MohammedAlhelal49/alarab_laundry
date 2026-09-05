/** @odoo-module **/

console.log(" Fallback banner loader starting...");

async function loadBanner() {
    try {
        const res = await fetch("/dekad/banner_message", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify({}),
        });

        const { result } = await res.json();
        console.log(" Banner result:", result);

        if (result?.enabled && result?.message) {
            const banner = document.createElement("div");
            banner.className = "alert alert-danger";
            banner.style.cssText = `
                margin: 0;
                padding: 14px;
                text-align: center;
                border-radius: 0;
                bottom: 0;
                left: 0;
                width: 100%;
                z-index: 99999 !important;
                background-color: #f8d7da;
                color: #721c24;
                font-weight: bold;
                width:100% !important;
             
                font-size:15px !important;
            `;
            banner.innerText = result.message;

            const closeBtn = document.createElement("span");
            closeBtn.innerHTML = "&times;";
            closeBtn.style.cssText = `
                position: absolute;
                right: 15px;
                bottom: 1px;
               width: 100% !important;
                font-size: 20px;
                
            `;
            closeBtn.onclick = () => banner.remove();
            // banner.appendChild(closeBtn);

            const container = document.querySelector(".o_web_client") || document.body;
            container.prepend(banner);

            console.log("✅ Banner injected!");
        }
    } catch (err) {
        console.error("❌ Failed to load banner", err);
    }
}

