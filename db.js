/**
 * BloodBridge JSON Database (localStorage-based)
 * Collections: bloodDonors, hospitalStaff, emergencyRequests
 */

const DB = {
    KEYS: {
        bloodDonors: 'bb_blood_donors',
        hospitalStaff: 'bb_hospital_staff',
        emergencyRequests: 'bb_emergency_requests'
    },

    _getAll(key) {
        try {
            return JSON.parse(localStorage.getItem(key)) || [];
        } catch { return []; }
    },

    _save(key, data) {
        localStorage.setItem(key, JSON.stringify(data));
    },

    _genId() {
        return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
    },

    // ── Blood Donors ──────────────────────────────────────
    addBloodDonor(record) {
        const donors = this._getAll(this.KEYS.bloodDonors);
        const entry = { id: this._genId(), ...record, createdAt: new Date().toISOString(), status: 'Pending' };
        donors.push(entry);
        this._save(this.KEYS.bloodDonors, donors);
        return entry;
    },
    getBloodDonors() { return this._getAll(this.KEYS.bloodDonors); },
    updateBloodDonorStatus(id, status) {
        const donors = this._getAll(this.KEYS.bloodDonors);
        const idx = donors.findIndex(d => d.id === id);
        if (idx !== -1) { donors[idx].status = status; this._save(this.KEYS.bloodDonors, donors); }
    },
    deleteBloodDonor(id) {
        const donors = this._getAll(this.KEYS.bloodDonors).filter(d => d.id !== id);
        this._save(this.KEYS.bloodDonors, donors);
    },

    // ── Hospital Staff ────────────────────────────────────
    addHospitalStaff(record) {
        const staff = this._getAll(this.KEYS.hospitalStaff);
        const entry = { id: this._genId(), ...record, createdAt: new Date().toISOString(), status: 'Pending' };
        staff.push(entry);
        this._save(this.KEYS.hospitalStaff, staff);
        return entry;
    },
    getHospitalStaff() { return this._getAll(this.KEYS.hospitalStaff); },
    updateHospitalStaffStatus(id, status) {
        const staff = this._getAll(this.KEYS.hospitalStaff);
        const idx = staff.findIndex(s => s.id === id);
        if (idx !== -1) { staff[idx].status = status; this._save(this.KEYS.hospitalStaff, staff); }
    },
    deleteHospitalStaff(id) {
        const staff = this._getAll(this.KEYS.hospitalStaff).filter(s => s.id !== id);
        this._save(this.KEYS.hospitalStaff, staff);
    },

    // ── Emergency Requests ────────────────────────────────
    addEmergencyRequest(record) {
        const reqs = this._getAll(this.KEYS.emergencyRequests);
        const entry = { id: this._genId(), ...record, createdAt: new Date().toISOString(), status: 'Active' };
        reqs.push(entry);
        this._save(this.KEYS.emergencyRequests, reqs);
        return entry;
    },
    getEmergencyRequests() { return this._getAll(this.KEYS.emergencyRequests); },
    updateEmergencyStatus(id, status) {
        const reqs = this._getAll(this.KEYS.emergencyRequests);
        const idx = reqs.findIndex(r => r.id === id);
        if (idx !== -1) { reqs[idx].status = status; this._save(this.KEYS.emergencyRequests, reqs); }
    },
    deleteEmergencyRequest(id) {
        const reqs = this._getAll(this.KEYS.emergencyRequests).filter(r => r.id !== id);
        this._save(this.KEYS.emergencyRequests, reqs);
    },

    // ── Stats ─────────────────────────────────────────────
    getStats() {
        const donors = this.getBloodDonors();
        const staff = this.getHospitalStaff();
        const emerg = this.getEmergencyRequests();
        return {
            totalDonors: donors.length,
            approvedDonors: donors.filter(d => d.status === 'Approved').length,
            pendingDonors: donors.filter(d => d.status === 'Pending').length,
            totalStaff: staff.length,
            approvedStaff: staff.filter(s => s.status === 'Approved').length,
            pendingStaff: staff.filter(s => s.status === 'Pending').length,
            totalEmergency: emerg.length,
            activeEmergency: emerg.filter(e => e.status === 'Active').length,
            resolvedEmergency: emerg.filter(e => e.status === 'Resolved').length,
        };
    },

    // ── Export ────────────────────────────────────────────
    exportAll() {
        return JSON.stringify({
            exportedAt: new Date().toISOString(),
            bloodDonors: this.getBloodDonors(),
            hospitalStaff: this.getHospitalStaff(),
            emergencyRequests: this.getEmergencyRequests()
        }, null, 2);
    }
};
