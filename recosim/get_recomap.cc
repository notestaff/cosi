#include <cstdio>
#include <cstdlib>
#include <cassert>
#include <cstring>
#include <boost/random/mersenne_twister.hpp>
#include <boost/random/uniform_01.hpp>
#include <boost/random/random_device.hpp>
#include <boost/integer/integer_mask.hpp>
#include <boost/cstdint.hpp>

int main(int argc, char **argv) {
  FILE *inf=NULL, *outf=NULL;
  char filename[256], *new_line=NULL, *running, *token;
  long seqlen, *pos, mapseq, pick_start;
  const int line_size = 256;
  int itoken, isite, max_site = 300000, nsite;
  double *rate=NULL;

	boost::mt19937 rand_engine;
	boost::uniform_01<> u01;
	boost::random_device rand_dev;
	
	boost::uint32_t seed = rand_dev() & boost::low_bits_mask_t<32>::sig_bits;
	rand_engine.seed( static_cast<boost::uint32_t>( seed ) );
  
  fprintf(stdout, "get_recomap rng seed: %lu\n", seed );
  new_line = (char *)malloc((line_size + 1) * sizeof(char));
  pos = (long int *)malloc(max_site * sizeof(long));
  rate = (double *)malloc(max_site * sizeof(double));
  if (argc != 4) {
    fprintf(stderr, "Usage: get_recomap <genetic map file> <sequence length (bp)> <output file>\n");
    exit(0);
  }
  seqlen = strtol(argv[2], NULL, 10);
  strcpy(filename, argv[1]);
  inf = fopen(filename, "r");
  if (inf == NULL) {
    fprintf(stderr, "Could not open requested file %s\n", filename);
    exit(0);
  }
  strcpy(filename, argv[3]);
  outf = fopen(filename, "w");
  if (outf == NULL) {
    fprintf(stderr, "Could not open requested file %s\n", filename);
    exit(0);
  }
  isite = 0;
  fgets(new_line, line_size, inf);
  while (fgets(new_line, line_size, inf) != NULL) {
    for (itoken = 0, running = new_line; (token = strsep(&running, " \t")) != NULL; itoken++) {
      if (itoken == 0) {
	pos[isite] = strtol(token, NULL, 10);
      }
      else if (itoken == 1) {
	rate[isite] = strtod(token, NULL);
	isite++;
	if (isite == max_site) {
	  max_site *= 2;
	  rate = (double *)realloc(rate, max_site * sizeof(double));
	  pos = (long int *)realloc(pos, max_site * sizeof(long));
	}
      }
    }
  }
  nsite = isite;
  //  fprintf(stderr, "n site: %d\n", nsite);
  mapseq = pos[nsite-1] - pos[0];
  assert(mapseq >= seqlen);
  //  fprintf(stderr, "in map: %ld   requested: %ld\n", mapseq, seqlen);
  pick_start = pos[0] + (long) ((mapseq - seqlen) * u01( rand_engine ) );
  isite = 0;
  while (pos[isite] < pick_start) {isite++;}
  if (pos[isite] == pick_start) {
    fprintf(outf, "1\t%.5e\n", 1.e-8 * rate[isite]);
    isite++;
  }  
  else {
    assert(isite > 0);
    fprintf(outf, "1\t%.5e\n", 1.e-8 * rate[isite-1]);
  }
  for (; isite < nsite; isite++) {
    if (pos[isite] >= pick_start + seqlen - 1) {break;}
    fprintf(outf, "%ld\t%.5e\n", pos[isite] - pick_start, 1.e-8 * rate[isite]);
  }


  return 0;
}
