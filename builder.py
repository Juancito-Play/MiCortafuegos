import os

files = {
    "settings.gradle": "rootProject.name = 'Cortafuegos'\ninclude ':app'\n",
    
    "build.gradle": """buildscript {
    repositories { google(); mavenCentral() }
    dependencies {
        classpath 'com.android.tools.build:gradle:8.1.2'
        classpath 'org.jetbrains.kotlin:kotlin-gradle-plugin:1.9.10'
    }
}
allprojects {
    repositories { google(); mavenCentral() }
}
""",

    "gradle.properties": "android.useAndroidX=true\norg.gradle.jvmargs=-Xmx2048m\n",

    "app/build.gradle": """plugins {
    id 'com.android.application'
    id 'org.jetbrains.kotlin.android'
}
android {
    namespace 'com.personal.cortafuegos'
    compileSdk 34
    defaultConfig {
        applicationId "com.personal.cortafuegos"
        minSdk 24
        targetSdk 34
        versionCode 3
        versionName "1.2"
    }
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = '17' }
}
dependencies {
    implementation 'androidx.core:core-ktx:1.12.0'
    implementation 'androidx.appcompat:appcompat:1.6.1'
}
""",

    "app/src/main/AndroidManifest.xml": """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.QUERY_ALL_PACKAGES" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <application
        android:allowBackup="true"
        android:label="Control Internet"
        android:supportsRtl="true"
        android:theme="@style/Theme.AppCompat.DayNight.DarkActionBar">
        <activity android:name=".MainActivity" android:exported="true" android:windowSoftInputMode="stateHidden">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        <service android:name=".FirewallVpnService"
            android:permission="android.permission.BIND_VPN_SERVICE"
            android:exported="false">
            <intent-filter>
                <action android:name="android.net.VpnService" />
            </intent-filter>
        </service>
    </application>
</manifest>
""",

    "app/src/main/java/com/personal/cortafuegos/MainActivity.kt": """package com.personal.cortafuegos

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.graphics.Color
import android.graphics.drawable.Drawable
import android.net.Uri
import android.net.VpnService
import android.os.Bundle
import android.provider.Settings
import android.text.Editable
import android.text.TextWatcher
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.*
import androidx.appcompat.app.AppCompatActivity

data class AppItem(val name: String, val packageName: String, val icon: Drawable, var internetEnabled: Boolean)

class MainActivity : AppCompatActivity() {
    private lateinit var prefs: android.content.SharedPreferences
    private val allAppsList = mutableListOf<AppItem>()
    private val filteredAppsList = mutableListOf<AppItem>()
    private lateinit var adapter: BaseAdapter
    private lateinit var countText: TextView

    private var currentSearchQuery = ""
    private var showOnlyBlocked = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = getSharedPreferences("firewall_prefs", Context.MODE_PRIVATE)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 20, 24, 16)
        }

        val searchInput = EditText(this).apply {
            hint = "🔍 Buscar aplicación..."
            isSingleLine = true
            setPadding(24, 20, 24, 20)
        }
        root.addView(searchInput, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT
        ))

        val filterCheckBox = CheckBox(this).apply {
            text = "Mostrar solo apps sin internet (OFF)"
            textSize = 15f
            setPadding(8, 16, 8, 8)
        }
        root.addView(filterCheckBox)

        val tipText = TextView(this).apply {
            text = "💡 Tip: Para que en WhatsApp salga 1 solo check (como teléfono apagado), ponla en OFF y toca 'Detener' para cerrarla por completo."
            textSize = 12f
            setTextColor(Color.parseColor("#E65100"))
            setPadding(12, 4, 12, 12)
        }
        root.addView(tipText)

        countText = TextView(this).apply {
            textSize = 13f
            setTextColor(Color.GRAY)
            setPadding(12, 4, 12, 16)
        }
        root.addView(countText)

        val listView = ListView(this)
        root.addView(listView, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT
        ))
        setContentView(root)

        loadInstalledApps()

        adapter = object : BaseAdapter() {
            override fun getCount(): Int = filteredAppsList.size
            override fun getItem(position: Int): Any = filteredAppsList[position]
            override fun getItemId(position: Int): Long = position.toLong()
            override fun getView(position: Int, convertView: View?, parent: ViewGroup?): View {
                val row = LinearLayout(this@MainActivity).apply {
                    orientation = LinearLayout.HORIZONTAL
                    gravity = Gravity.CENTER_VERTICAL
                    setPadding(12, 16, 12, 16)
                }
                val item = filteredAppsList[position]

                val iconView = ImageView(this@MainActivity).apply {
                    setImageDrawable(item.icon)
                    layoutParams = LinearLayout.LayoutParams(95, 95).apply { rightMargin = 24 }
                }
                val nameView = TextView(this@MainActivity).apply {
                    text = item.name
                    textSize = 15f
                    layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
                }

                // Botón para abrir ajustes de la app y forzar detención si está en OFF
                val stopBtn = Button(this@MainActivity).apply {
                    text = "Detener"
                    textSize = 11f
                    visibility = if (!item.internetEnabled) View.VISIBLE else View.GONE
                    setOnClickListener {
                        val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                            data = Uri.fromParts("package", item.packageName, null)
                        }
                        startActivity(intent)
                    }
                }

                val toggle = Switch(this@MainActivity).apply {
                    setOnCheckedChangeListener(null)
                    isChecked = item.internetEnabled
                    text = if (isChecked) "ON " else "OFF "
                    setTextColor(if (isChecked) Color.parseColor("#2E7D32") else Color.parseColor("#C62828"))
                    
                    setOnCheckedChangeListener { _, isChecked ->
                        item.internetEnabled = isChecked
                        saveBlockedState(item.packageName, !isChecked)
                        applyFirewallRules()
                        filterApps()
                    }
                }
                row.addView(iconView)
                row.addView(nameView)
                row.addView(stopBtn)
                row.addView(toggle)
                return row
            }
        }
        listView.adapter = adapter

        searchInput.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                currentSearchQuery = s?.toString()?.trim() ?: ""
                filterApps()
            }
            override fun afterTextChanged(s: Editable?) {}
        })

        filterCheckBox.setOnCheckedChangeListener { _, isChecked ->
            showOnlyBlocked = isChecked
            filterApps()
        }

        filterApps()

        if (getBlockedSet().isNotEmpty()) {
            applyFirewallRules()
        }
    }

    private fun loadInstalledApps() {
        val pm = packageManager
        val blockedSet = getBlockedSet()
        val packages = pm.getInstalledApplications(0)
        allAppsList.clear()
        for (app in packages) {
            val isSystem = (app.flags and ApplicationInfo.FLAG_SYSTEM) != 0
            val isUpdatedSystem = (app.flags and ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) != 0
            if ((!isSystem || isUpdatedSystem) && app.packageName != packageName) {
                val label = pm.getApplicationLabel(app).toString()
                val icon = pm.getApplicationIcon(app)
                val isBlocked = blockedSet.contains(app.packageName)
                allAppsList.add(AppItem(label, app.packageName, icon, !isBlocked))
            }
        }
        allAppsList.sortWith(compareBy<AppItem> { it.internetEnabled }.thenBy { it.name.lowercase() })
    }

    private fun filterApps() {
        filteredAppsList.clear()
        val query = currentSearchQuery.lowercase()
        var blockedCount = 0

        for (app in allAppsList) {
            if (!app.internetEnabled) blockedCount++
            val matchesQuery = query.isEmpty() || app.name.lowercase().contains(query)
            val matchesFilter = !showOnlyBlocked || !app.internetEnabled

            if (matchesQuery && matchesFilter) {
                filteredAppsList.add(app)
            }
        }
        countText.text = "Mostrando ${filteredAppsList.size} de ${allAppsList.size} apps  •  Bloqueadas (OFF): $blockedCount"
        adapter.notifyDataSetChanged()
    }

    private fun getBlockedSet(): MutableSet<String> {
        return prefs.getStringSet("blocked_packages", emptySet())?.toMutableSet() ?: mutableSetOf()
    }

    private fun saveBlockedState(pkg: String, blocked: Boolean) {
        val set = getBlockedSet()
        if (blocked) set.add(pkg) else set.remove(pkg)
        prefs.edit().putStringSet("blocked_packages", set).commit()
    }

    private fun applyFirewallRules() {
        val intent = VpnService.prepare(this)
        if (intent != null) {
            startActivityForResult(intent, 100)
        } else {
            onActivityResult(100, Activity.RESULT_OK, null)
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 100 && resultCode == Activity.RESULT_OK) {
            val serviceIntent = Intent(this, FirewallVpnService::class.java)
            startService(serviceIntent)
        }
    }
}
""",

    "app/src/main/java/com/personal/cortafuegos/FirewallVpnService.kt": """package com.personal.cortafuegos

import android.content.Context
import android.content.Intent
import android.net.VpnService
import android.os.ParcelFileDescriptor
import android.system.OsConstants
import java.io.FileInputStream

class FirewallVpnService : VpnService() {
    private var vpnInterface: ParcelFileDescriptor? = null
    @Volatile private var isRunning = false
    private var workerThread: Thread? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        restartVpn()
        return START_STICKY
    }

    private fun restartVpn() {
        stopVpnThread()

        val prefs = getSharedPreferences("firewall_prefs", Context.MODE_PRIVATE)
        val blocked = prefs.getStringSet("blocked_packages", emptySet()) ?: emptySet()

        if (blocked.isEmpty()) {
            stopSelf()
            return
        }

        val builder = Builder()
            .setSession("CortafuegosPersonal")
            // Bloqueo IPv4
            .addAddress("10.1.10.1", 32)
            .addRoute("0.0.0.0", 0)
            .addDnsServer("10.1.10.2")
            // Bloqueo IPv6 (Clave para datos móviles y Wi-Fi modernos)
            .addAddress("fd00:1:fd00:1:fd00:1:fd00:1", 128)
            .addRoute("::", 0)
            .addDnsServer("fd00:1:fd00:1:fd00:1:fd00:2")
            .allowFamily(OsConstants.AF_INET)
            .allowFamily(OsConstants.AF_INET6)
            .setBlocking(true)

        for (pkg in blocked) {
            try { builder.addAllowedApplication(pkg) } catch (_: Exception) {}
        }

        vpnInterface = builder.establish()

        // Hilo "Agujero Negro": lee y destruye todos los paquetes para que nada salga ni entre
        vpnInterface?.let { vpn ->
            isRunning = true
            workerThread = Thread {
                val input = FileInputStream(vpn.fileDescriptor)
                val buffer = ByteArray(32767)
                while (isRunning) {
                    try {
                        val length = input.read(buffer)
                        if (length <= 0) Thread.sleep(50)
                    } catch (_: Exception) {
                        break
                    }
                }
            }.apply { start() }
        }
    }

    private fun stopVpnThread() {
        isRunning = false
        try { vpnInterface?.close() } catch (_: Exception) {}
        vpnInterface = null
        try { workerThread?.interrupt() } catch (_: Exception) {}
        workerThread = null
    }

    override fun onDestroy() {
        stopVpnThread()
        super.onDestroy()
    }
}
"""
}

for path, content in files.items():
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print("Archivos actualizados con bloqueo IPv6 y drenaje de paquetes.")
