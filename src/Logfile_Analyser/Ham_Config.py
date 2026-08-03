from pathlib import Path

LOG_FOLDER = Path(r"\\file01-s0\0.051 Research & Development\Instrumentation\Logfiles\Hamilton")  # <-- Logfile location
LOG_FOLDER = Path(r"W:\0.051 Research & Development\Instrumentation\Logfiles\Hamilton")  # <-- Logfile location
# LOG_FOLDER = Path(r"C:\Users\ch33\Documents\Hamilton")


PROCESSED_FOLDER = LOG_FOLDER / "Processed"
MOVE_FILES_AFTER_PARSE = True


OUTPUT_FILE = LOG_FOLDER / "CondensedLogs_Raw.csv" 
TIDY_OUTPUT_FILE = LOG_FOLDER / "TidyLogs_ForTableau.csv"
TABLEAU_FILE = LOG_FOLDER / "TidyLogs.hyper"

TRACE_FOLDER = LOG_FOLDER / "Traces"
PYTHON_LOG_FILE = TRACE_FOLDER / "python_logs.txt"
STALE_INSTRUMENTS = TRACE_FOLDER / "stale_instruments.txt"

TABLEAU_SERVER_ADDRESS = "https://globalreporting.internal.sanger.ac.uk"
TABLEAU_SITE_ID = ""
TABLEAU_PROJECT_ID = "0c88cccd-6f5c-4cd5-9641-f01c10fdbc3e"
TABLEAU_DATA_NAME = "Hamilton Tidy Logs"

DAYS_BEFORE_STALE = 45

# =========================================================================
# STEPS TO RUN - flip any of these to False to skip that step
# =========================================================================

STEPS_TO_RUN = {
    "parse_logs":   True,   # Condense traces into a single .csv
    "clean_logs":   True,   # Tidy raw csv into a Tableau-ready csv
    "create_hyper": True,   # Convert tidy csv into a hyper file
    "publish":      True,   # Push hyper file to Tableau server
    "check_stale":  True,   # Create a warning if an instrument has gone quiet for too long
}

# =========================================================================
# CONFIG - the settings you're most likely to want to change
# =========================================================================

FILENAME_PREFIXES_TO_DROP = (
    "HxUsbComm",
    "ComTrace_Simulator",
    "Hamilton Backup Utility",
)

STATUSES_TO_DROP = {
    "Read Error",
    "No Start Found"
}

PROCESS_TYPES = {
    "Clean Up": {
        "16S_PostPCR_CleanUp": [
            "16S_POSTPCR_CLEANUP",
        ],
        "1_PLATE_10X_PSI_1X_SPRI": [
            "1_PLATE_10X_PSI_1X_SPRI_V0.2",
            "1_PLATE_10X_PSI_1X_SPRI_V0.3",
            "1_PLATE_10X_PSI_1X_SPRI_V0.3_H4",
            "1_PLATE_10X_PSI_1X_SPRI_V0.4_H4",
        ],
        "1_PLATE_10X_PSI_2X_SPRI": [
            "1_PLATE_10X_PSI_2X_SPRI",
            "1_PLATE_10X_PSI_2X_SPRI_SVL2",
            "1_PLATE_10X_PSI_2X_SPRI_SVL3",
            "1_PLATE_10X_PSI_2X_SPRI_SVL3_H4",
            "1_PLATE_10X_PSI_2X_SPRI_SVL4",
        ],
        "1_PLATE_2xSPRI_LowInput": [
            "1_PLATE_LOW_INPUT_2X_SPRI",
        ],
        "1_PLATE_2xSPRI_ISC_LowInput": [
            "1_PLATE_2XSPRI_ISC_LOW_INPUT",
        ],
        "1_PLATE_BOTSEQ_PCR_XP": [
            "1_PLATE_BOTSEQ_PCR_XP",
            "1_PLATE_BOTSEQ_PCR_XP_H4",
            "1_PLATE_BOTSEQ_PCR_XP_H4_SVL_TRANSFORMER PLATE AS SOURCE",
        ],
        "1_PLATE_FFPE_ISC_PCR_XP": [
            "1_PLATE_FFPE_ISC_PCR_XP",
            "1_PLATE_FFPE_ISC_PCR_XP_STAR6"
        ],
        "1_PLATE_FFPE_ISC_POST_CAP_PCR_XP": [
            "1_PLATE_FFPE_ISC_POST_CAP_PCR_XP",
            "1_PLATE_FFPE_ISC_POST_CAP_PCR_XP_STAR6"
        ],
        "1_PLATE_ISC_PCR_XP": [
            "ISC_PCR_XP",
            "1_PLATE_ISC_PCR_XP",
            "1_PLATE_ISC_PCR_XP_STAR6",
            "1_BIORAD_PLATE_ISC_PCR_XP",
            "1_BIORAD_PLATE_ISC_PCR_XP_STAR6",
        ],
        "1_PLATE_ISC_POST_CAP_PCR_XP": [
            "1_PLATE_ISC_POST_CAP_PCR_XP",
            "1_PLATE_ISC_POST_CAP_PCR_XP_STAR6",
            "1_BIORAD_PLATE_ISC_POST_CAP_PCR_XP",
            "1_BIORAD_PLATE_ISC_POST_CAP_PCR_XP_STAR6",
        ],
        "1_PLATE_LCMB_ISC_PCR_XP": [
            "1_PLATE_LCMB_ISC_PCR_XP",
            "1_PLATE_LCMB_ISC_PCR_XP_STAR6",
            "1_BIORAD_PLATE_LCMB_ISC_PCR_XP",
            "1_BIORAD_PLATE_LCMB_ISC_PCR_XP_STAR6",
        ],
        "1_PLATE_LCMB_WGS_PCR_XP": [
            "1_PLATE_LCMB_WGS_PCR_XP",
            "1_PLATE_LCMB_WGS_PCR_XP_STAR6",
            "1_BIORAD_PLATE_LCMB_WGS_PCR_XP",
            "1_BIORAD_PLATE_LCMB_WGS_PCR_XP_STAR6",
        ],
        "1_PLATE_WGS_PCR_XP": [
            "1_PLATE_WGS_PCR_XP",
            "1_PLATE_WGS_PCR_XP_STAR6",
            "1_BIORAD_PLATE_WGS_PCR_XP",
            "1_BIORAD_PLATE_WGS_PCR_XP_STAR6",
        ],
        "1_PLATE_RNA_PCR_XP": [
            "1_PLATE_RNA_PCR_XP",
            "1_PLATE_RNA_PCR_XP_CLEANUP_IN_TWINTEC"
        ],
        "2_PLATE_BOTSEQ_PCR_XP": [
            "2_PLATE_BOTSEQ_PCR_XP",
        ],
        "2_PLATE_FFPE_ISC_PCR_XP": [
            "2_PLATE_FFPE_ISC_PCR_XP",
            "2_PLATE_FFPE_ISC_PCR_XP_STAR6",
        ],
        "2_PLATE_FFPE_ISC_POST_CAP_PCR_XP": [
            "2_PLATE_FFPE_ISC_POST_CAP_PCR_XP",
            "2_PLATE_FFPE_ISC_POST_CAP_PCR_XP_STAR6",
        ],
        "2_PLATE_ISC_PCR_XP": [
            "2_PLATE_ISC_PCR_XP",
            "2_PLATE_ISC_PCR_XP_STAR6",
            "2_BIORAD_PLATE_ISC_PCR_XP",
            "2_BIORAD_PLATE_ISC_PCR_XP_STAR6",
        ],
        "2_PLATE_ISC_POST_CAP_PCR_XP": [
            "2_PLATE_ISC_POST_CAP_PCR_XP",
            "2_PLATE_ISC_POST_CAP_PCR_XP_STAR6",
            "2_BIORAD_PLATE_ISC_POST_CAP_PCR_XP",
            "2_BIORAD_PLATE_ISC_POST_CAP_PCR_XP_STAR6",
        ],
        "2_PLATE_LCMB_ISC_PCR_XP": [
            "2_PLATE_LCMB_ISC_PCR_XP",
            "2_PLATE_LCMB_ISC_PCR_XP_STAR6",
            "2_BIORAD_PLATE_LCMB_ISC_PCR_XP",
            "2_BIORAD_PLATE_LCMB_ISC_PCR_XP_STAR6",
        ],
        "2_PLATE_LCMB_WGS_PCR_XP": [
            "2_PLATE_LCMB_WGS_PCR_XP",
            "2_PLATE_LCMB_WGS_PCR_XP_STAR6",
            "2_BIORAD_PLATE_LCMB_WGS_PCR_XP",
            "2_BIORAD_PLATE_LCMB_WGS_PCR_XP_STAR6",
        ],
        "2_PLATE_WGS_PCR_XP": [
            "2_PLATE_WGS_PCR_XP",
            "2_PLATE_WGS_PCR_XP_STAR6",
            "2_BIORAD_PLATE_WGS_PCR_XP",
            "2_BIORAD_PLATE_WGS_PCR_XP_STAR6",
        ],
        "2_PLATE_10X_PSI_2X_SPRI": [
            "2_PLATE_10X_PSI_2X_SPRI",
        ],
        "384WGS_PostShear_XP": [
            "384WGS_POSTSHEAR_XPBIORAD",
            "384WGS_POSTSHEAR_XPBIORAD_V1.0",
            "384 WGS POST SHEAR XP V0.1",
            "384 WGS POST SHEAR XP_BIORAD V0.1",
            "384 WGS POST SHEAR XP_BIORAD V0.4",
        ],
        "384 PF Post Shear XP": [
            "384 PF POST SHEAR XP V0.1",
            "384 PF POST SHEAR XP V0.1.BACKUP200319",
            "384 PF POST SHEAR XP_BIORAD V0.1",
        ],
        "384 PF Post Shear XP Consolidation": [
            "384 PF POST SHEAR XP_CONSOLIDATION_V0.1",
            "384 PF POST SHEAR XP_CONSOLIDATION_V0.2",
        ],
        "384_RLT_XP": [
            "384_RLT_XP_V0.1",
        ],
        "96 wells bead clean": [
            "IB3 96 WELLS BEAD CLEAN",
            "IB3 96 WELLS BEAD CLEAN V2",
            "96 WELLS BEAD CLEAN",
        ],
        "AMPure CleanUp 384 Plate": [
            "AMPURE CLEANUP 384 WELL PLATE V1.3",
            "AMPURE CLEANUP 384 WELL PLATE V1.4",
            "AMPURE CLEANUP 384 WELL PLATE V1.2",
            "AMPURE CLEANUP 384 WELL PLATE V1.6",
            "AMPURE CLEANUP 384 WELL PLATE V1.7",
        ],
        "CLCM_EM_PCR_XP": [
            "CLCM_EM_PCR_XP_STAR6",
        ],
        "Double-Sided SPRI": [
            "DOUBLE-SIDED SPRI V1.0",
            "DOUBLE-SIDED SPRI V1.1_SVL",
            "DOUBLE-SIDED SPRI V1.10_SVL",
            "DOUBLE-SIDED SPRI V1.11_SVL",
            "DOUBLE-SIDED SPRI V1.11_SVL_FOR TESTS ONLY",
            "DOUBLE-SIDED SPRI V1.12_SVL",
            "DOUBLE-SIDED SPRI V1.13_3METHOD OPTION_SVL",
            "DOUBLE-SIDED SPRI V1.14_3METHOD OPTION_SVL_IB3",
            "DOUBLE-SIDED SPRI V1.14_3METHOD OPTION_SVL_REVERSION TO SPRI LLD",
            "DOUBLE-SIDED SPRI V1.15_3METHOD OPTION_SVL_IB3",
            "DOUBLE-SIDED SPRI V1.16_3METHOD OPTION_SVL_IB3",
            "DOUBLE-SIDED SPRI V1.2_SVL",
            "DOUBLE-SIDED SPRI V1.3_SVL",
            "DOUBLE-SIDED SPRI V1.4_SVL",
            "DOUBLE-SIDED SPRI V1.5_SVL",
            "DOUBLE-SIDED SPRI V1.6_SVL",
            "DOUBLE-SIDED SPRI V1.7_SVL",
            "DOUBLE-SIDED SPRI V1.8",
            "DOUBLE-SIDED SPRI V1.8_QUICK PLATE MOVEMENT",
            "DOUBLE-SIDED SPRI V1.9_SVL",
        ],
        "Generic_SPRI_CleanUp": [
            "GENERIC_BEAD_CLEANUP",
            "GENERIC_SPRI_CLEANUP",
        ],
        "RVI_BC_POST_CAPTURE_XP_0.8X": [
            "RVI_BC_POST_CAPTURE_XP_0.8X_STAR4",
            "RVI_BC_POST_CAPTURE_XP_0.8X_STAR5",
            "RVI_BC_POST_CAPTURE_XP_0.8X_STAR6",
        ],
        "RVI_BC_LIBRARY_CAPTURE_PCR_XP_1X": [
            "RVI_BC_LIBRARY_CAPTURE_PCR_XP_1X_STAR4",
            "RVI_BC_LIBRARY_CAPTURE_PCR_XP_1X_STAR5",
            "RVI_BC_LIBRARY_CAPTURE_PCR_XP_1X_STAR6",
        ],
        "Single-Sided SPRI": [
            "SINGLE-SIDED SPRI V1.0",
            "SINGLE-SIDED SPRI V1.1",
            "SINGLE-SIDED SPRI V1.10_IB3_3METHOD OPTION",
            "SINGLE-SIDED SPRI V1.10_IB3_3METHOD OPTION_REVERSION TO SPRI LLD",
            "SINGLE-SIDED SPRI V1.11_IB3_3METHOD OPTION",
            "SINGLE-SIDED SPRI V1.11A_IB3_3METHOD OPTION",
            "SINGLE-SIDED SPRI V1.12_IB3_3METHOD OPTION",
            "SINGLE-SIDED SPRI V1.13_IB3_3METHOD OPTION",
            "SINGLE-SIDED SPRI V1.2_SVL",
            "SINGLE-SIDED SPRI V1.3_SVL",
            "SINGLE-SIDED SPRI V1.4_SVL",
            "SINGLE-SIDED SPRI V1.5_SVL",
            "SINGLE-SIDED SPRI V1.6",
            "SINGLE-SIDED SPRI V1.7_SVL",
            "SINGLE-SIDED SPRI V1.7_SVL_AJ",
            "SINGLE-SIDED SPRI V1.8_SVL_3METHOD OPTION",
            "SINGLE-SIDED SPRI V1.9_SVL_3METHOD OPTION",
        ],
        "scRNA Core Post cDNA Amp Cleanup": [
            "SCRNA CORE POST CDNA AMP CLEANUP_V1",
            "SCRNA CORE POST CDNA AMP CLEANUP_V2",
            "SCRNA CORE POST CDNA AMP CLEANUP_V3",
        ],
        "Ultima_SingleSidedCleanUp": [
            "ULTIMA_SINGLESIDEDCLEANUP",
            "ULTIMA_SINGLESIDEDCLEANUPV1.1",
        ],
        "Ultima_DoubleSidedCleanUp": [
            "ULTIMA_DOUBLESIDEDCLEANUP",
        ],
        "WorkFlow CleanupOnly": [
            "WORKFLOW CLEANUPONLY V1.2",
            "WORKFLOW CLEANUPONLY V1.3",
            "WORKFLOW CLEANUPONLY V1.4",
            "WORKFLOW CLEANUPONLY V1.6",
            "WORKFLOW CLEANUPONLY V1.7",
        ],
    },
    "Extraction": {
        "BeadExtraction_NoCooledCarriers": [
            "BEADEXTRACTION_NOCOOLEDCARRIERS_STAR#495DV1.0.2",
            "BEADEXTRACTION_NOCOOLEDCARRIERS_STAR#495DV1.0.3",
            "BEADEXTRACTION_NOCOOLEDCARRIERS_STAR#495DV1.0.4",
            "BEADEXTRACTION_NOCOOLEDCARRIERS_STAR#495DV1.0.5",
            "BEADEXTRACTION_NOCOOLEDCARRIERS_STAR#495DV1.0.6",
            "BEADEXTRACTION_NOCOOLEDCARRIERS_STAR#495DV1.0.7",
            "BEADEXTRACTION_NOCOOLEDCARRIERS_STAR#495DV1.0.8",
            "BEADEXTRACTION_NOCOOLEDCARRIERS_STAR#495DV1.0.8RECOVERY",
            "BEADEXTRACTION_NOCOOLEDCARRIERS_STAR#495DV1.0.9",
            "BEADEXTRACTION_NOCOOLEDCARRIERS_V1.0.0_KEEPTIPS",
            "BEADEXTRACTION_NOCOOLEDCARRIERS_V1.0.1_KEEPTIPS",
        ],
        "BeadExtraction_NTR_CooledCarriers": [
            "BEADEXTRACTION_NTR_COOLEDCARRIERS_STAR#261B_V1.0.0",
            "BEADEXTRACTION_NTR_COOLEDCARRIERS_STAR#7721_V1.0.0",
            "BEADEXTRACTION_NTR_NOCOOLEDCARRIERS_STAR#495D_V1.0.0",
        ],
        "Crick_BeadExtraction": [
            "CRICK_BEADEXTRACTION__STAR#495D_V0.0.1",
            "CRICK_BEADEXTRACTION__STAR#495D_V0.0.2",
        ],
    },
    "Sample Dilution": {
        "Redilute Echo Plate": [
            "REDILUTE CONCENTRATED ECHO SOURCE PLATE V1.0",
            "REDILUTE CONCENTRATED ECHO SOURCE PLATE V1.1",
        ],
        "BotSeq_Sample Dilution": [
            "BOT-SEQ_SAMPLE_DILUTION V1.10_UNIVERSAL DILUTION SCRIPT DIRECT AND INDIRECT_TIP LOCATION_NAPOLEON",
            "BOT-SEQ_SAMPLE_DILUTION V1.11_UNIVERSAL DILUTION SCRIPT DIRECT AND INDIRECT_TIP LOCATION_NAPOLEON",
            "BOT-SEQ_SAMPLE_DILUTION V1.12_UNIVERSAL DILUTION SCRIPT DIRECT AND INDIRECT_TIP LOCATION_NAPOLEON",
            "BOT-SEQ_SAMPLE_DILUTION V1.5",
            "BOT-SEQ_SAMPLE DILUTION V1.5",
            "BOT-SEQ_SAMPLE DILUTION V1.5_25UL FINAL VOLUME",
            "BOT-SEQ_SAMPLE DILUTION V1.5_UNIVERSAL DILUTION SCRIPT",
            "BOT-SEQ_SAMPLE DILUTION V1.6_UNIVERSAL DILUTION SCRIPT DIRECT AND INDIRECT",
            "BOT-SEQ_SAMPLE DILUTION V1.7_UNIVERSAL DILUTION SCRIPT DIRECT AND INDIRECT_TIP LOCATION",
            "BOT-SEQ_SAMPLE DILUTION V1.7_UNIVERSAL DILUTION SCRIPT DIRECT AND INDIRECT_TIP LOCATION_NAPOLEON",
            "BOT-SEQ_SAMPLE DILUTION V1.8_UNIVERSAL DILUTION SCRIPT DIRECT AND INDIRECT_TIP LOCATION_SLOWER 36UL DISP",
            "BOT-SEQ_SAMPLE DILUTION V1.9_UNIVERSAL DILUTION SCRIPT DIRECT AND INDIRECT_TIP LOCATION",
            "BOT-SEQ_SAMPLE DILUTION V1.9_UNIVERSAL DILUTION SCRIPT DIRECT AND INDIRECT_TIP LOCATION_NAPOLEON",
            "BOT-SEQ_SAMPLE_DILUTION V1.6_UNIVERSAL DILUTION SCRIPT DIRECT AND INDIRECT",
            "BOT-SEQ_SAMPLE_DILUTION V1.7_UNIVERSAL DILUTION SCRIPT DIRECT AND INDIRECT_TIP LOCATION",
            "BOT-SEQ_SAMPLE_DILUTION V1.8_UNIVERSAL DILUTION SCRIPT DIRECT AND INDIRECT_TIP LOCATION_SLOWER 36UL DISP",
            "BOT-SEQ_SAMPLE_DILUTION V1.9_UNIVERSAL DILUTION SCRIPT DIRECT AND INDIRECT_TIP LOCATION",
            "BOT-SEQ_SAMPLE_DILUTION V1.9_UNIVERSAL DILUTION SCRIPT DIRECT AND INDIRECT_TIP LOCATION_NAPOLEON",
            "BOT-SEQ_SAMPLE DILUTION V1.10_UNIVERSAL DILUTION SCRIPT DIRECT AND INDIRECT_TIP LOCATION_NAPOLEON",
            "BOT-SEQ_SAMPLE DILUTION V1.11_UNIVERSAL DILUTION SCRIPT DIRECT AND INDIRECT_TIP LOCATION_NAPOLEON",
            "BOT-SEQ_SAMPLE DILUTION V1.12_UNIVERSAL DILUTION SCRIPT DIRECT AND INDIRECT_TIP LOCATION_NAPOLEON"
        ],
        "SampleNormalisation_CherryPicking": [
            "SAMPLENORMALISATION_CHERRYPICKING",
        ],
        "Sample Dilution": [
            "SAMPLE DILUTION V1.0",
            "SAMPLE DILUTION V1.1",
            "SAMPLE DILUTION V1.2",
            "SAMPLE DILUTION V1.3 AFTER ANDY CHANGES",
            "SAMPLE DILUTION V1.4",
            "SAMPLE DILUTION V1.5",
            "SAMPLE DILUTION V2.0",
            "SAMPLE DILUTION_QUICK METHOD",
        ],
        "SGE-MAVE_SampleDilution": [
            "SGE_SAMPLEDILUTION_V2.0",
        ],
        "LibraryDilution": [
            "LIBRARYDILUTION_V0.1",
            "LIBRARYDILUTION_V0.2",
            "LIBRARYDILUTION_V0.3",
            "LIBRARYDILUTION_V0.3IRAAD",
            "LIBRARYDILUTION_V0.4",
            "LIBRARYDILUTION_V0.4HEATHER",
            "LIBRARYDILUTION_V0.5",
            "LIBRARYDILUTION_V0.6",
            "LIBRARYDILUTION_V0.7",
            "LIBRARYDILUTION_V0.8",
            "LIBRARYDILUTION_V0.9",
            "LIBRARYDILUTION_V0.91",
            "LIBRARYDILUTION_V0.92",
            "LIBRARYDILUTION_V0.93 CHANGED PLATE OUTLOOK",
            "LIBRARYDILUTION_V0.93",
            "LIBRARYDILUTION_V1.0",
        ],
    },
    "Pooling": {
        "LoadToFC_SangerInstitute_Plates": [
            "LOADTOFC_SANGERINSTITUTE_PLATES_V0.2",
        ],
        "LoadToFC_SangerInstitute_Tubes": [
            "LOADTOFC_SANGERINSTITUTE_TUBES_V0.1",
            "LOADTOFC_SANGERINSTITUTE_TUBES_V0.4",
            "LOADTOFC_SANGERINSTITUTE_TUBES_V1.1",
            "LOADTOFC_SANGERINSTITUTE_TUBES_V1.2",
            "LOADTOFC_SANGERINSTITUTE_TUBES_V1.3",
        ],
        "PoolSample": [
            "POOLSAMPLE_V1",
            "POOLSAMPLE_V2",
            "POOLSAMPLE_V2.1",
            "POOLSAMPLE_V2.2",
            "POOLSAMPLE_V2.3",
            "POOLSAMPLE_V2.4",
            "POOLSAMPLE_V2.4A",
            "POOLSAMPLE_V2.4A MODIFIED FOR TESTING",
            "POOLSAMPLE_V2.5",
            "POOLSAMPLE_V2.5STARLAB",
            "POOLSAMPLE_V2.6",
            "POOLSAMPLE_V2.6A",
            "POOLSAMPLE_V2.6B",
            "POOLSAMPLE_V2.6B_FINAL",
            "POOLSAMPLE_V2.6B_TEST",
            "POOLSAMPLE_V2.7",
            "POOLSAMPLE_V2.7_NXT",
            "POOLSAMPLES_V3.0",
            "POOLSAMPLES_V3.2",
            "POOLSAMPLES_V5.0",
            "POOLSAMPLES_V5.1",
            "POOLSAMPLES_V6",
            "POOLSAMPLES_V7",
        ],
        "Pooling Sangerised": [
            "Pooling",
            "POOLING SANGERISED",
            "POOLING SANGERISED V2",
            "POOLING SANGERISED2",
        ],
        "96 Pool Sample": [
            "96POOLSAMPLE_V1.1",
            "96POOLSAMPLE_V1",
            "96POOLSAMPLE_V2.1",
            "96POOLSAMPLE_V2.2 INTERMEDIATE",
            "96POOLSAMPLE_V2.2",
            "96POOLSAMPLE_V2.3",
            "96POOLSAMPLE_V2",
            "96POOLSAMPLE_V3.1",
            "96POOLSAMPLE_V3",
            "POOL96WELLPLATE_V1.0"
        ],
        "Bioscan_SamplesPooling_384toTubes": [
            "BIOSCAN_SAMPLESPOOLING_384TOTUBES_V0",
        ],
        "COVID-19_PoolSamples_96w": [
            "COVID-19_POOLSAMPLES_96W_V0.1",
            "COVID-19_POOLSAMPLES_96W_V0.1_HIGHDILUTE",
            "COVID-19_POOLSAMPLES_96W_V0.1_HIGHELUTE",
            "COVID-19_POOLSAMPLES_96W_V0.2_HIGHDILUTE",
            "COVID-19_POOLSAMPLES_96W_V0.3_HIGHDILUTE",
            "COVID-19_POOLSAMPLES_96W_V0.4_HIGHDILUTE",
            "COVID-19_POOLSAMPLES_V0.10_HIGHDILUTE_BEDVER_OGILVIE_H4",
            "COVID-19_POOLSAMPLES_V0.10_HIGHDILUTE_BEDVER_OGILVIE_H5",
            "COVID-19_POOLSAMPLES_V0.11_HIGHDILUTE_BEDVER_OGILVIE_H4",
            "COVID-19_POOLSAMPLES_V0.12_HIGHDILUTE_BEDVER_OGILVIE_H4",
            "COVID-19_POOLSAMPLES_V0.12_HIGHDILUTE_BEDVER_OGILVIE_H5",
        ],
        "COVID-19_PoolSamples": [
            "COVID-19_POOLSAMPLES_V0.2",
            "COVID-19_POOLSAMPLES_V0.3",
            "COVID-19_POOLSAMPLES_V0.4",
            "COVID-19_POOLSAMPLES_V0.5",
            "COVID-19_POOLSAMPLES_V0.5_H5",
            "COVID-19_POOLSAMPLES_V0.5_HIGHDILUTE",
            "COVID-19_POOLSAMPLES_V0.5_HIGHELUTE",
            "COVID-19_POOLSAMPLES_V0.6_HIGHDILUTE_H5",
            "COVID-19_POOLSAMPLES_V0.6_HIGHDILUTE_HERONLAB",
            "COVID-19_POOLSAMPLES_V0.7_HIGHDILUTE_BEDVER_H4",
            "COVID-19_POOLSAMPLES_V0.8_HIGHDILUTE_BEDVER_OGILVIE_H4",
            "COVID-19_POOLSAMPLES_V0.8_HIGHDILUTE_BEDVER_OGILVIE_H5",
            "COVID-19_POOLSAMPLES_V0.8_HIGHDILUTE_OGILVIE_H4",
            "COVID-19_POOLSAMPLES_V0.8_HIGHDILUTE_OGILVIE_H5",
            "COVID-19_POOLSAMPLES_V0.9_HIGHDILUTE_BEDVER_OGILVIE_H4",
            "COVID-19_POOLSAMPLES_V0.9_HIGHDILUTE_BEDVER_OGILVIE_H5",
        ],
        "COVID-19_PoolSamples_Q1only": [
            "COVID-19_POOLSAMPLES_Q1ONLY_V0.3_HIGHDILUTE_H4",
            "COVID-19_POOLSAMPLES_Q1ONLY_V0.3_HIGHDILUTE_H5",
            "COVID-19_POOLSAMPLES_Q1ONLY_V0.4_HIGHDILUTE_BEDVER_H4",
            "COVID-19_POOLSAMPLES_Q1ONLY_V0.5_HIGHDILUTE_BEDVER_OGILVIE_H4",
            "COVID-19_POOLSAMPLES_Q1ONLY_V0.5_HIGHDILUTE_BEDVER_OGILVIE_H5",
            "COVID-19_POOLSAMPLES_Q1ONLY_V0.5_HIGHDILUTE_OGILVIE_H4",
            "COVID-19_POOLSAMPLES_Q1ONLY_V0.5_HIGHDILUTE_OGILVIE_H5",
        ],
        "PoolSample_Single_Plate": [
            "PoolSample_single_plate_V1_NXT",
            "PoolSample_single_plate_V1",
        ],
        "pWGS_384_PoolSamples": [
            "PWGS_384_POOLSAMPLES_V1.0",
        ],
        "Pool384Plates": [
            "Pool384Platesv1",
        ],
    },
    "Cherry Picking": {
        "Cherry Pick": [
            "CHERRY PICK V1.0",
            "CHERRY PICK V1.1_SVL",
            "CHERRY PICK V1.1_SVL_AJ",
            "CHERRY PICK V1.1_SVL_NAPOLEON",
            "CHERRY PICK V1.2_IB3",
            "CHERRY PICK V1.2_IB3_SVL",
            "CHERRY PICK V1.2_SVL_NAPOLEON",
            "CHERRY PICK V1.3_IB3",
            "CHERRY PICK V1.4_IB3_SVL",
            "CHERRY PICK V1.4_IB3_SVL_NAPOLEON",
            "CHERRY PICK V1.5_IB3_SVL_NAPOLEON",
        ],
        "Cherrypicking_COVID": [
            "CHERRYPICKING_COVID_BIORAD_V0.8",
            "CHERRYPICKING_COVID_BIORAD_V0.9",
            "CHERRYPICKING_COVID_BIORAD_V1.0",
            "CHERRYPICKING_COVID_V0.3",
            "CHERRYPICKING_COVID_V0.4",
            "CHERRYPICKING_COVID_V0.5",
            "CHERRYPICKING_COVID_V0.6",
            "CHERRYPICKING_COVID_V0.7",
            "CHERRYPICKING_COVID_V0.8",
            "CHERRYPICKING_COVID_V0.9",
            "CHERRYPICKING_COVID_V1.0",
        ],
        "SGE-MAVE_Cherrypick_EppendorfPlateTo3Plates": [
            "SGE-MAVE_CHERRYPICK_EPPENDORFPLATETO3PLATES",
        ],
    },
    "Testing": {
        "Gravimetric Testing": [
            "ROCKET TIP GRAVIMETRIC",
            "ROCKET TIP GRAVIMETRIC BABE",
            "300UL_TIP_GRAVIMETRIC",
            "GRAVIMETRIC BABE",
            "GRAVIMETRIC POST PCR CHANNELS",
            "GRAVIMETRIC 8 CHANNELS",
            "GRAVIMETRIC 96 HEAD",
            "SANGER_384HEAD ARTEL V1.0",
            "SANGER_ARTEL MVS FOR CHANNELS AND MPH96 V2.7",
        ],
        "384 HeadCheck": [
            "384 HEADCHECK",
            "384 HEAD CHECK",
            "384 HEAD CHECK 1",
            "384_HEAD_UNIFORMITY_PIPETTING_TEST",
        ],
        "Shearing Tests": [
            "SHEARING TESTS",
            "SHEARING TESTS V0.2",
            "SHEARING TESTS V0.3",
            "SHEARING TESTS V0.4",
            "SHEARING TESTS v0.5",
            "SHEARING TESTS V0.6",
            "SHEARING TESTS v0.7",
            "SHEARING TESTS v0.8",
            "SHEARING TESTS v0.9",
            "SHEARING TESTS v0.10",
            "Shearing tests v0.10 hack",
        ],
        "Other": [
            "96 HEAD FLATNESS",
            "96 HEAD STOP DISK CHNAGE TEST",
            "AT_TESTMETHOD",
            "Single-Sided SPRI v1.7_SVL_AJtest",
            "Grips",
            "Fluidigm_Chip_Teaching_Test_v1.0",
            "BOO",
            "CH_TEST",
            "CLLD TEST",
            "CLLD TESTING",
            "Single-Sided SPRI VDJ Z error test",
            "PlatePiercing_v1",
            "CLOSE YOUR JAWS",
            "DOWNHOLDERPIPETTING_V1",
            "ALCOHOL_HANDLING_TEST_010520",
            "AP_AFTERPM_TEST",
            "GRIPPER USE TEST FOR NTRS",
            "GRIPPERTESTCOPY",
            "HAMHEATERSHAKER_CHECK",
            "INHECO ODTC HSL DEMO",
            "METHOD1",
            "USERINPUTS V1.3",
            "USERINPUTS V1.7",
            "ROCKET TEST",
            "TEMPABBYTESTDOORLOCK",
            "TEST1",
            "METHODTEST",
            "SANGER VERSION CONTROL",
            "HACK",
            "PLATE MOVES",
            "PLATEMOVES",
            "PLATEMOVESTEST",
            "FUMBLES",
            "SHORT PIPETTING SCRIPT",
            "SM TEST",
            "SPRI QUICK METHOD",
            "STARLINEDAILYMAINTENANCE",
            "STARLINEWEEKLYMAINTENANCE",
            "TEMPEH11",
            "TEST",
            "TEST_BARCODE_SCANNER",
            "TEST_SOS",
            "TESTMETHOD",
            "TESTNUCPLATE_384 96X50UL",
            "TIP HANDLING",
            "VERIFICATION_2",
            "EXPORTSEQTOEXCEL",
            "UVDECONTAMINATIONSTAR2",
            "HOW TO PICKUP A PLATE",
            "MIX TRANSFER TEST",
            "LIQUID_TEST_CLEAR_TIPS",
            "HSL HONEYWELL ORBIT DEMO",
        ],
    },
    "Plate Stamping": {
        "Plate Stamping": [
            "PLATE STAMPING V1.4",
            "PLATE STAMPING V1.5",
            "PLATE STAMPING V1.6",
            "PLATE STAMPING V1.7",
            "PLATE STAMPING V1.8",
            "PLATE STAMPING V1.8B",
            "PLATE STAMPING V1.9",
        ],
        "Heron_96_to_384_consolidation": [
            "HERON_96_TO_384_CONSOLIDATION.V1.0",
        ],
        "Combine 4x96": [
            "COMBINE 4X96_1.1",
            "COMBINE 4X96_1.2",
            "COMBINE 4X96_1.3",
            "COMBINE 4X96_1.4",
            "COMBINE 4X96_1.4B",
            "COMBINE 4X96_LOW_QUALITY_FIX_1.2",
            "COMBINE_4X96_1.1",
            "COMBINE_4X96_1.2",
            "COMBINE_4X96_1.3",
            "COMBINE_4X96_1.4",
            "COMBINE_4X96_1.4B",
            "COMBINE_4X96_LOW_QUALITY_FIX_1.2",
        ],
        "Axygen_3x384to12x96_quadrants_STAR": [
            "AXYGEN_3X384TO12X96_QUADRANTS_STAR_V1.1",
        ],
    }
}

FIELDS = [
    ("instrument", "Instrument"),
    ("filename", "Filename"),
    ("start_time", "Start Time"),
    ("end_time", "End Time"),
    ("status", "Status"),
    ("sim_mode", "Sim Mode"),
    ("method", "Method"),
]

TIDY_FIELDS = [
    ("instrument", "Instrument", "text"),
    ("filename", "Filename", "text"),
    ("start_time", "Start Time", "datetime"),
    ("end_time", "End Time", "datetime"),
    ("status", "Status", "text"),
    ("sim_mode", "Sim Mode", "text"),
    ("method", "Method", "text"),
    ("run_duration_minutes", "Run Duration (min)", "float"),
    ("run_date", "Run Date", "date"),
    ("process_type", "Process Type", "text"),
    ("method_simplified", "Method Simp.", "text")
]