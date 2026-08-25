#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

void download_on_the_spot(const char *flight, const char *api_key) {
    char cmd[512];
    char filename[128];
    long int timestamp = (long int)time(NULL);

    // Format output storage target instantly with explicit boundaries
    snprintf(filename, sizeof(filename), "downloads/spot_flight_%s_%ld.json", flight, timestamp);
    
    // Explicit API payload layout distribution containing formatting tags
    snprintf(cmd, sizeof(cmd), 
             "curl -s -X GET \"http://aviationstack.com\" -o %s", 
             api_key, flight, filename);

    printf("⚡ [ENGINE] Processing live capture for Flight: %s...\n", flight);
    system("mkdir -p downloads");
    
    if (system(cmd) == 0) {
        printf("✅ [ENGINE] Saved payload on the bloody spot -> %s\n", filename);
    } else {
        fprintf(stderr, "❌ [ENGINE] Ingestion failure.\n");
    }
}

int main(int argc, char *argv[]) {
    if (argc < 3) {
        // Fix pointer layout mismatch safely
        fprintf(stderr, "Usage: %s <FLIGHT_IATA> <API_KEY>\n", argv[0]);
        return 1;
    }
    download_on_the_spot(argv[1], argv[2]);
    return 0;
}
